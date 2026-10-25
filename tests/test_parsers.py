import pytest

from streamstats.errors import (
    InvalidEventError,
    StreamStatsError,
    UnsupportedFormatError,
)
from streamstats.parsers import read_events

FIRST_EVENT = {
    "timestamp": "2026-10-14T10:00:00Z",
    "level": "INFO",
    "source": "web",
    "message": "старт сервиса",
}


def read_all(path, file_format):
    return list(read_events(path, file_format, False, [0]))


def test_jsonl_parser_reads_events(data):
    events = read_all(data("events.jsonl"), "jsonl")

    assert len(events) == 6
    assert events[0] == FIRST_EVENT
    assert events[-1]["level"] == "DEBUG"


def test_csv_parser_reads_events(data):
    events = read_all(data("events.csv"), "csv")

    assert len(events) == 6
    assert events[0] == FIRST_EVENT
    assert events[-1]["level"] == "DEBUG"


@pytest.mark.parametrize("file_format", ["csv", "jsonl"])
def test_empty_file_yields_no_events(data, file_format):
    assert read_all(data(f"empty.{file_format}"), file_format) == []


@pytest.mark.parametrize("file_format", ["csv", "jsonl"])
def test_unicode_is_preserved(data, file_format):
    events = read_all(data(f"unicode.{file_format}"), file_format)

    assert events[0]["source"] == "Логирование"
    assert events[0]["message"] == "Ошибка: не удалось сохранить файл"
    assert events[1]["message"] == "Привет, мир! ёЁ"


def test_csv_without_required_column_raises(data):
    with pytest.raises(InvalidEventError, match="message"):
        read_all(data("bad_header.csv"), "csv")


def test_unsupported_format_raises(data):
    with pytest.raises(UnsupportedFormatError):
        read_all(data("events.jsonl"), "xml")


def test_missing_file_raises_streamstats_error(tmp_path):
    with pytest.raises(StreamStatsError, match="nope.jsonl"):
        read_all(str(tmp_path / "nope.jsonl"), "jsonl")


def test_parser_reads_lazily(data):
    stream = read_events(data("bad_json_line7.jsonl"), "jsonl", False, [0])

    for _ in range(6):
        next(stream)
    with pytest.raises(InvalidEventError):
        next(stream)
