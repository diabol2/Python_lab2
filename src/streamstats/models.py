from datetime import datetime, timezone
from typing import Any

from streamstats.errors import InvalidEventError, InvalidTimestampError

LEVELS: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
ERROR_LEVELS: tuple[str, ...] = ("ERROR", "CRITICAL")
REQUIRED_FIELDS: tuple[str, ...] = ("timestamp", "level", "source", "message")

Event = dict[str, str]


def parse_timestamp(value: str) -> datetime:
    """Разобрать ISO 8601. Метка без часового пояса считается UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise InvalidTimestampError(
            f"Неверная метка времени в поле timestamp: {value!r}"
        ) from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def validate_event(event: Any) -> Event:
    """Проверить обязательные поля события и вернуть его же."""
    if not isinstance(event, dict):
        raise InvalidEventError("Событие должно быть объектом (словарём)")

    for field in REQUIRED_FIELDS:
        if field not in event:
            raise InvalidEventError(f"Отсутствует поле {field}")
        if not isinstance(event[field], str):
            raise InvalidEventError(f"Поле {field} должно быть строкой")

    if event["level"] not in LEVELS:
        raise InvalidEventError(f"Неизвестный уровень в поле level: {event['level']!r}")
    if not event["source"].strip():
        raise InvalidEventError("Поле source не должно быть пустым")

    parse_timestamp(event["timestamp"])
    return event
