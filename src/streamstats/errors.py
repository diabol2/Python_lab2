class StreamStatsError(Exception):
    """Базовая ошибка пакета."""


class UnsupportedFormatError(StreamStatsError):
    """Запрошен формат входного файла, который не поддерживается."""


class InvalidEventError(StreamStatsError):
    """Событие не прошло валидацию (или строка не разобралась)."""


class InvalidTimestampError(InvalidEventError):
    """Временная метка события не соответствует ISO 8601."""


class CliConfigError(StreamStatsError):
    """Некорректная конфигурация запуска CLI."""
