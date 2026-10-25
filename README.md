# streamstats: потоковый анализатор событий

Читает события из CSV и JSONL **построчно**, не загружая файл в память, и строит
JSON-отчёт со статистикой. Несколько входных файлов объединяются в один отчёт.

## Установка и запуск

```bash
pip install -e ".[dev]"

python -m streamstats --help
python -m streamstats analyze a.csv b.csv --format csv --output report.json
python -m streamstats analyze logs.jsonl --format jsonl --skip-invalid
python -m streamstats analyze logs.jsonl --format jsonl --top 10
```

| Параметр | Назначение |
|---|---|
| `INPUT ...` | один или несколько входных файлов (все в одном формате) |
| `--format csv\|jsonl` | формат входных файлов |
| `--output PATH` | путь к отчёту, по умолчанию `report.json` |
| `--skip-invalid` | пропускать повреждённые строки вместо остановки |
| `--top N` | размер списка источников ошибок, по умолчанию 5 |

Коды возврата: `0` успех, `2` ошибка данных, файла или конфигурации (в stderr
выводится сообщение с именем файла и номером строки).

## Модель события

| Поле | Требование |
|---|---|
| `timestamp` | ISO 8601 (`2026-10-14T10:00:00Z`, `...+02:00`); без пояса считается UTC |
| `level` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `source` | непустая строка |
| `message` | строка (может быть пустой) |

CSV должен содержать заголовок с этими четырьмя колонками. JSONL: один JSON-объект
на строку, пустые строки игнорируются. Кодировка файлов: UTF-8.

## Формат отчёта

```json
{
    "total_events": 3,
    "levels": {"DEBUG": 0, "INFO": 1, "WARNING": 0, "ERROR": 1, "CRITICAL": 1},
    "sources": {"srv": 1, "db": 2},
    "first_timestamp": "2026-10-14T09:00:00Z",
    "last_timestamp": "2026-10-14T11:00:00Z",
    "skipped_lines": 0,
    "top_error_sources": [{"source": "db", "count": 2}]
}
```

`top_error_sources` считает только `ERROR` и `CRITICAL`; сортировка по убыванию
счётчика, при равенстве по имени источника.
Первая и последняя метки определяются по моменту времени, а не по тексту, поэтому
`12:00+02:00` корректно считается раньше `11:00Z`.

## Обработка ошибочных строк

- **По умолчанию**: обработка останавливается, в stderr печатается
  `файл, строка N: причина`, код возврата `2`, отчёт не создаётся.
- **`--skip-invalid`**: строка пропускается, в лог пишется `WARNING` с файлом и
  строкой, число пропусков попадает в `skipped_lines`.

## Архитектура

```text
src/streamstats/
  errors.py    иерархия исключений (StreamStatsError и наследники)
  models.py    LEVELS, parse_timestamp, validate_event
  parsers.py   read_events(): генератор событий для CSV/JSONL
  analysis.py  create_stats / add_events / finish_stats
  report.py    запись JSON
  __main__.py  CLI (argparse), граница обработки ошибок
```

## Потоковость и память

- `read_events` это генератор: файл открывается через `with open(...)` и читается
  циклом `for line in file` (JSONL) / `csv.DictReader` (CSV); `read()` без лимита и
  `readlines()` не используются.
- `add_events` обновляет только счётчики, события нигде не накапливаются.
- Дополнительная память: O(1) на поток событий плюс O(U) на словари счётчиков, где
  U число **уникальных источников**. Она не зависит ни от числа событий, ни от
  размера файла.

## Тесты и проверки

```bash
python -m pytest
ruff check .
python -m streamstats --help
```

Тесты работают на реальных файлах: входные данные лежат в `tests/data/`, а ожидаемые
отчёты в `tests/verified/`.

```text
tests/
  data/        входные CSV/JSONL: обычные, пустые, Unicode, битые, с часовыми поясами
  verified/    эталонные JSON-отчёты для golden-тестов
  test_parsers.py   unit-тесты обоих парсеров, пустые файлы, Unicode, ленивость
  test_errors.py    строгий режим и --skip-invalid, номер файла и строки в ошибке
  test_reports.py   golden: CLI на файлах из data/ == отчёт из verified/
  test_cli.py       коды возврата, неизменность исходников, subprocess, большой файл
```

Каждый тест пишет результат только в свой `tmp_path`, файлы в `tests/data/` не
изменяются (это проверяется отдельным тестом). Порядок запуска не важен.
Эталон CSV и JSONL для одних и тех же событий общий (`events.json`), поэтому
эквивалентность форматов проверяется напрямую.
