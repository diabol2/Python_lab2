import logging

import pytest

from streamstats.errors import InvalidEventError, InvalidTimestampError
from streamstats.parsers import read_events


def read_all(path, file_format, skip_invalid):
    skipped = [0]
    events = list(read_events(path, file_format, skip_invalid, skipped))
    return events, skipped[0]


def test_bad_json_reports_file_and_line_7(data):
    with pytest.raises(InvalidEventError) as exc_info:
        read_all(data("bad_json_line7.jsonl"), "jsonl", skip_invalid=False)

    assert "bad_json_line7.jsonl" in str(exc_info.value)
    assert "строка 7" in str(exc_info.value)


@pytest.mark.parametrize(
    ("name", "file_format", "line"),
    [
        ("bad_timestamp.jsonl", "jsonl", "строка 2"),
        ("bad_timestamp.csv", "csv", "строка 3"),
    ],
)
def test_bad_timestamp_reports_field_and_line(data, name, file_format, line):
    with pytest.raises(InvalidTimestampError) as exc_info:
        read_all(data(name), file_format, skip_invalid=False)

    message = str(exc_info.value)
    assert "timestamp" in message
    assert line in message
    assert name in message


def test_strict_mode_stops_at_first_bad_line(data):
    received = []

    with pytest.raises(InvalidEventError):
        for event in read_events(data("bad_json_line7.jsonl"), "jsonl", False, [0]):
            received.append(event)

    assert len(received) == 6


def test_skip_invalid_keeps_remaining_lines(data):
    events, skipped = read_all(data("bad_json_line7.jsonl"), "jsonl", True)

    assert len(events) == 7
    assert skipped == 1
    assert events[-1]["message"] == "after bad line"


def test_skip_invalid_writes_warning_with_file_and_line(data, caplog):
    with caplog.at_level(logging.WARNING):
        read_all(data("bad_json_line7.jsonl"), "jsonl", True)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "bad_json_line7.jsonl" in warnings[0].getMessage()
    assert "строка 7" in warnings[0].getMessage()


def test_skip_invalid_handles_every_kind_of_bad_line(data):
    events, skipped = read_all(data("invalid_mixed.jsonl"), "jsonl", True)

    assert len(events) == 2
    assert skipped == 6
