import hashlib
import os
import shutil
import subprocess
import sys
import tracemalloc
from pathlib import Path

from streamstats.__main__ import main

SRC = Path(__file__).resolve().parents[1] / "src"
DATA_DIR = Path(__file__).resolve().parent / "data"


def run_module(*args, cwd):
    env = {**os.environ, "PYTHONPATH": str(SRC), "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, "-m", "streamstats", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=cwd,
    )


def test_cyrillic_is_kept_readable_in_report_file(tmp_path, data):
    output = tmp_path / "report.json"

    main(["analyze", data("unicode.jsonl"), "--format", "jsonl",
          "--output", str(output)])

    raw = output.read_text(encoding="utf-8")
    assert "Логирование" in raw


def test_invalid_line_stops_with_code_2_and_no_report(tmp_path, data, capsys):
    output = tmp_path / "report.json"

    code = main(["analyze", data("bad_json_line7.jsonl"), "--format", "jsonl",
                 "--output", str(output)])

    stderr = capsys.readouterr().err
    assert code == 2
    assert "bad_json_line7.jsonl" in stderr
    assert "строка 7" in stderr
    assert not output.exists()


def test_report_cannot_overwrite_input_file(tmp_path, data, capsys):
    victim = tmp_path / "input.jsonl"
    shutil.copy(data("events.jsonl"), victim)
    before = victim.read_bytes()

    code = main(["analyze", str(victim), "--format", "jsonl", "--output", str(victim)])

    assert code == 2
    assert victim.read_bytes() == before
    assert "перезаписывать" in capsys.readouterr().err


def test_source_files_are_never_modified(tmp_path, data):
    def snapshot():
        return {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in DATA_DIR.iterdir()
        }

    before = snapshot()
    runs = [
        ("events.jsonl", []),
        ("invalid_mixed.jsonl", ["--skip-invalid"]),
        ("bad_json_line7.jsonl", []),
    ]
    for name, extra in runs:
        main(["analyze", data(name), "--format", "jsonl",
              "--output", str(tmp_path / "r.json"), *extra])

    assert snapshot() == before


def test_help_exits_with_zero(tmp_path):
    result = run_module("--help", cwd=tmp_path)

    assert result.returncode == 0
    assert "analyze" in result.stdout


def test_process_exit_code_is_2_on_invalid_line(tmp_path, data):
    result = run_module("analyze", data("bad_json_line7.jsonl"), "--format", "jsonl",
                        "--output", "r.json", cwd=tmp_path)

    assert result.returncode == 2
    assert "строка 7" in result.stderr


def test_large_file_is_streamed_not_loaded(tmp_path):
    big = tmp_path / "big.jsonl"
    line = (
        '{"timestamp": "2026-10-14T10:00:00Z", "level": "ERROR", '
        '"source": "svc-%d", "message": "Сообщение номер %d"}\n'
    )
    with big.open("w", encoding="utf-8") as file:
        for i in range(100_000):
            file.write(line % (i % 20, i))
    file_size = big.stat().st_size

    tracemalloc.start()
    code = main(["analyze", str(big), "--format", "jsonl",
                 "--output", str(tmp_path / "r.json")])
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert code == 0
    assert peak < file_size / 10
