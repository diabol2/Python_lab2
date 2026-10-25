import json
from typing import Any


def save_report(report: dict[str, Any], output_path: str) -> None:
    """Запись JSON-отчёта."""
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=4)
        file.write("\n")
