from datetime import datetime
from typing import Any

from streamstats.models import ERROR_LEVELS, LEVELS, Event, parse_timestamp

Stats = dict[str, Any]


def create_stats() -> Stats:
    """Создает и возвращает словарь с начальной структурой статистики."""
    return {
        "total_events": 0,
        "levels": {level: 0 for level in LEVELS},
        "sources": {},
        "error_sources": {},
        "first_timestamp": None,
        "last_timestamp": None,
        "skipped_lines": 0,
        "_first_date": None,
        "_last_date": None,
    }


def _bump(counters: dict[str, int], key: str) -> None:
    """Увеличивает счетчик для указанного ключа на единицу."""
    counters[key] = counters.get(key, 0) + 1


def add_events(stats: Stats, event: Event) -> None:
    """Учесть одно событие в статистике."""
    stats["total_events"] += 1

    level = event["level"]
    source = event["source"]
    timestamp = event["timestamp"]

    stats["levels"][level] += 1
    _bump(stats["sources"], source)
    if level in ERROR_LEVELS:
        _bump(stats["error_sources"], source)

    moment: datetime = parse_timestamp(timestamp)
    if stats["_first_date"] is None or moment < stats["_first_date"]:
        stats["first_timestamp"] = timestamp
        stats["_first_date"] = moment
    if stats["_last_date"] is None or moment > stats["_last_date"]:
        stats["last_timestamp"] = timestamp
        stats["_last_date"] = moment


def finish_stats(stats: Stats, top_n: int = 5) -> Stats:
    """Собрать итоговый отчёт (исходный словарь stats не изменяется)."""
    ranked = sorted(
        stats["error_sources"].items(), key=lambda item: (-item[1], item[0])
    )

    report = {
        key: value
        for key, value in stats.items()
        if key != "error_sources" and not key.startswith("_")
    }
    report["top_error_sources"] = [
        {"source": source, "count": count} for source, count in ranked[:top_n]
    ]
    return report
