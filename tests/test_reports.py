import json

import pytest

from streamstats.__main__ import main

CASES = [
    ("events_jsonl", ["events.jsonl"], "jsonl", [], "events"),
    ("events_csv", ["events.csv"], "csv", [], "events"),
    ("empty_jsonl", ["empty.jsonl"], "jsonl", [], "empty"),
    ("unicode_jsonl", ["unicode.jsonl"], "jsonl", [], "unicode"),
    ("multi_files", ["events.jsonl", "second.jsonl"], "jsonl", [], "multi"),
    ("tz_offsets", ["tz_offsets.jsonl"], "jsonl", [], "tz_offsets"),
    ("top_ties", ["top_ties.jsonl"], "jsonl", [], "top_ties"),
    ("top_3", ["top_ties.jsonl"], "jsonl", ["--top", "3"], "top_ties_top3"),
    ("skip_bad_json", ["bad_json_line7.jsonl"], "jsonl", ["--skip-invalid"],
     "bad_json_skip"),
    ("skip_bad_date_csv", ["bad_timestamp.csv"], "csv", ["--skip-invalid"],
     "bad_timestamp_skip"),
    ("skip_mixed", ["invalid_mixed.jsonl"], "jsonl", ["--skip-invalid"],
     "invalid_mixed_skip"),
]


@pytest.mark.parametrize(
    ("inputs", "file_format", "extra", "verified"),
    [case[1:] for case in CASES],
    ids=[case[0] for case in CASES],
)
def test_report_matches_verified(
    tmp_path, data, expected, inputs, file_format, extra, verified
):
    output = tmp_path / "report.json"
    args = ["analyze", *[data(name) for name in inputs]]
    args += ["--format", file_format, "--output", str(output), *extra]

    code = main(args)

    assert code == 0
    assert json.loads(output.read_text(encoding="utf-8")) == expected(verified)
