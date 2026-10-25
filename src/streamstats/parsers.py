import csv
import json
import logging
from collections.abc import Iterator
from typing import TextIO

from streamstats.errors import (
    InvalidEventError,
    StreamStatsError,
    UnsupportedFormatError,
)
from streamstats.models import REQUIRED_FIELDS, Event, validate_event

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = ("csv", "jsonl")


def _handle_invalid(
    error: StreamStatsError,
    path: str,
    line_number: int,
    skip_invalid: bool,
    skipped: list[int],
) -> None:
    """Обработать повреждённую строку в зависимости от режима.

    Строгий режим (skip_invalid=False): пробрасывает исключение того же типа,
    добавив в сообщение имя файла и номер строки.
    Режим пропуска (skip_invalid=True): увеличивает счётчик skipped[0] и пишет
    WARNING с файлом и строкой, обработка продолжается.
    """
    if not skip_invalid:
        raise type(error)(f"{path}, строка {line_number}: {error}") from error
    skipped[0] += 1
    logger.warning("%s, строка %s: %s", path, line_number, error)


def _iter_csv(
    file: TextIO, path: str, skip_invalid: bool, skipped: list[int]
) -> Iterator[Event]:
    """Лениво читать события из открытого CSV-файла.

    Проверяет наличие обязательных колонок в заголовке, затем читает записи
    по одной через csv.DictReader и валидирует каждую.
    """
    reader = csv.DictReader(file)
    if reader.fieldnames is None:
        return

    missing = [name for name in REQUIRED_FIELDS if name not in reader.fieldnames]
    if missing:
        raise InvalidEventError(
            f"{path}, строка 1: в CSV отсутствуют заголовки: {', '.join(missing)}"
        )

    while True:
        try:
            row = next(reader)
        except StopIteration:
            return
        except csv.Error as error:
            raise InvalidEventError(
                f"{path}, строка {reader.line_num}: {error}"
            ) from error

        try:
            event = validate_event(row)
        except StreamStatsError as error:
            _handle_invalid(error, path, reader.line_num, skip_invalid, skipped)
            continue
        yield event


def _iter_jsonl(
    file: TextIO, path: str, skip_invalid: bool, skipped: list[int]
) -> Iterator[Event]:
    """Лениво читать события из открытого JSONL-файла.

    Файл читается построчно (for line in file), каждая строка разбирается как
    JSON и валидируется.
    """
    for line_number, line in enumerate(file, start=1):
        if not line.strip():
            continue
        try:
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as error:
                raise InvalidEventError(f"Некорректный JSON: {error}") from error
            event = validate_event(raw)
        except StreamStatsError as error:
            _handle_invalid(error, path, line_number, skip_invalid, skipped)
            continue
        yield event


def read_events(
    path: str, file_format: str, skip_invalid: bool, skipped: list[int]
) -> Iterator[Event]:
    """Лениво читать события из файла.

    skipped - список из одного числа: сюда накапливается счётчик пропущенных строк.
    """
    if file_format not in SUPPORTED_FORMATS:
        raise UnsupportedFormatError(f"Неподдерживаемый формат файла: {file_format}")

    try:
        with open(path, encoding="utf-8", newline="") as file:
            if file_format == "csv":
                yield from _iter_csv(file, path, skip_invalid, skipped)
            else:
                yield from _iter_jsonl(file, path, skip_invalid, skipped)
    except UnicodeDecodeError as error:
        raise InvalidEventError(
            f"{path}: файл не в кодировке UTF-8: {error}"
        ) from error
    except OSError as error:
        raise StreamStatsError(f"Не удалось прочитать файл {path}: {error}") from error
