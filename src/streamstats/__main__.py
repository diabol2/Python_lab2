"""CLI: python -m streamstats analyze INPUT [INPUT ...] --format csv|jsonl."""

import argparse
import logging
import os
import sys
from collections.abc import Sequence

from streamstats.analysis import add_events, create_stats, finish_stats
from streamstats.errors import CliConfigError, StreamStatsError
from streamstats.parsers import SUPPORTED_FORMATS, read_events
from streamstats.report import save_report


def build_parser() -> argparse.ArgumentParser:
    """Парсер аргументов CLI.

    Создаёт подкоманду analyze с параметрами INPUT, --format, --output,
    --skip-invalid и --top, а также подменяет текст справки на собственный.
    """
    epilog = ('Анализатор файлов\n\n'
              'Поддерживаемые форматы файлов:\n'
              'csv и jsonl\n\n'
              'Примеры команд для использования:\n'
              'python -m streamstats analyze INPUT [INPUT ...]'
              ' --format csv|jsonl --output REPORT.json\n'
              'python -m streamstats analyze INPUT --format jsonl --skip-invalid\n'
              'python -m streamstats analyze INPUT --format jsonl --top 3\n'
              'python -m streamstats --help'
             )

    parser = argparse.ArgumentParser(prog="streamstats",
        epilog=epilog,
        formatter_class = argparse.RawDescriptionHelpFormatter
    )

    def custom_print_help(file=None):
        target_file = sys.stdout if file is None else file
        target_file.write(parser.epilog + "\n")

    parser.print_help = custom_print_help

    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze")
    analyze.add_argument("inputs", nargs="+", metavar="INPUT")
    analyze.add_argument("--format", choices=SUPPORTED_FORMATS, required=True)
    analyze.add_argument("--output", default="report.json")
    analyze.add_argument(
        "--skip-invalid",
        action="store_true"
    )
    analyze.add_argument("--top", type=int, default=5)
    return parser


def _check_config(args: argparse.Namespace) -> None:
    """Проверить параметры запуска до чтения файлов.

    Проверяет, что --top не меньше 1 и что файл отчёта не совпадает
    с одним из входных файлов, а также выдаст ошибку если
    параметры заданы некорректно.
    """
    if args.top < 1:
        raise CliConfigError("--top должен быть не меньше 1")
    for path in args.inputs:
        both_exist = os.path.exists(path) and os.path.exists(args.output)
        if both_exist and os.path.samefile(path, args.output):
            raise CliConfigError(f"Отчёт не может перезаписывать входной файл: {path}")


def _analyze(args: argparse.Namespace) -> dict:
    """Прочитать все входные файлы потоком и вернуть готовый отчёт.

    События обрабатываются по одному и не накапливаются в памяти, хранятся
    только счётчики. Число пропущенных строк берётся из общего счётчика
    по всем файлам.
    """
    stats = create_stats()
    skipped = [0]
    for path in args.inputs:
        for event in read_events(path, args.format, args.skip_invalid, skipped):
            add_events(stats, event)
    stats["skipped_lines"] = skipped[0]
    return finish_stats(stats, top_n=args.top)


def main(argv: Sequence[str] | None = None) -> int:
    """Точка входа CLI: разобрать аргументы, построить отчёт и сохранить его.

    Передаваемые аргументы:
        argv: аргументы командной строки; None означает sys.argv.

    Возвращает:
        0 при успехе, 2 при ошибке данных, файла или конфигурации
        (сообщение об ошибке выводится в stderr).
    """
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    try:
        _check_config(args)
        report = _analyze(args)
        save_report(report, args.output)
    except StreamStatsError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"Ошибка файла отчёта: {error}", file=sys.stderr)
        return 2

    print(f"Обработано событий: {report['total_events']}")
    print(f"Пропущено строк: {report['skipped_lines']}")
    print(f"Отчёт сохранён: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
