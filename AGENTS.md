# AGENTS.md

Ежедневный mirror OpenAPI-схемы Ozon Seller API: fetcher на Camoufox качает `docs.ozon.ru/api/seller/swagger.json` за Qrator, cron коммитит изменения в main и синхронизирует блок схемы в README.

## Стек

- Python 3.14 + Poetry, flat layout (`ozon_schema_fetcher/` в корне репо)
- Camoufox (stealth Firefox поверх Playwright) — обход JS-челленджа Qrator; обычный HTTP-клиент получает 307 на страницу челленджа
- Dev-группа: pytest, ruff (расширенный ruleset, `target-version = py314`), mypy strict, pre-commit
- Docker: multi-stage `python:3.14-slim-trixie`; браузер качается на этапе сборки (`python -m camoufox fetch`)

## Команды

Все команды — из корня через `make` (см. `make help`); эквиваленты без make — в скобках.

| Команда | Что делает |
|---|---|
| `make install` | установка зависимостей (`poetry install --with dev`) |
| `make fetch` | скачать схему → `schemas/ozon-seller-api-openapi.json` (`poetry run python -m ozon_schema_fetcher -o ...`) |
| `make test` | pytest |
| `make lint` | pre-commit по всем файлам: ruff-format + ruff + mypy |
| `make docker-build` | сборка образа `ozon-schema-fetcher` (`docker build -t ozon-schema-fetcher .`) |
| `make docker-fetch` | скачивание схемы через Docker-образ → `schemas/` |

## Структура

- `ozon_schema_fetcher/` — пакет: `fetcher.py` (навигация + body-sniff до JSON, ретраи со сном до дедлайна), `validation.py`, `__main__.py` (CLI: `-o/--out`, `--url`, `--timeout-ms`, `--headed`)
- `tests/` — pytest; импорт `scripts/update_readme.py` в тестах — через `importlib.util.spec_from_file_location` (scripts/ не пакет)
- `scripts/update_readme.py` — генератор блока схемы в README между маркерами `<!-- SCHEMA-BEGIN -->` / `<!-- SCHEMA-END -->` (stdlib only)
- `schemas/ozon-seller-api-openapi.json` — закоммиченное зеркало схемы; коммитит cron при изменении
- `.github/workflows/` — `ci.yml` (lint+test+docker), `update-schema.yml` (cron)
- `Dockerfile`, `Makefile`, `.pre-commit-config.yaml`, `pyproject.toml`

## Конвенции

- ruff и mypy покрывают `ozon_schema_fetcher tests scripts`; хуки pre-commit прокидывают эти же каталоги (`ruff check ozon_schema_fetcher tests scripts`, `mypy ozon_schema_fetcher tests scripts`), ruff-format форматирует всё
- PEP 758 (target py314): запятая без скобок (`except ValueError, Error:`) допустима только без `as` — так пишет `ruff format`; с `as` скобки обязательны (`except ValueError, Error as e:` — SyntaxError), а скобочная форма (`except (ValueError, Error) as e:`) всегда валидна
- В `scripts/` нельзя `print` (ruff T20) — тихий exit 0; `print` разрешён только в `__main__.py` (per-file-ignore в pyproject)
- CLI пишет схему атомарно (tmp + `Path.replace`), дедлайн-таймауты в мс

## CI

- `ci.yml` — push в main + все PR: job `lint-test` (Python 3.14, poetry==2.3.2, `pre-commit run -a`, pytest) и job `docker` (`docker/build-push-action@v6`, `push: false`, `load: true`, gha-кэш `scope=ozon-schema-fetcher`, smoke-тест `docker run ... --help`)
- `update-schema.yml` — cron `0 0 * * *` + `workflow_dispatch`, `permissions: contents: write`: сборка образа (тот же gha-кэш) → `docker run ... -o /schemas/ozon-seller-api-openapi.json` → при изменении схемы `scripts/update_readme.py` + коммит в main (`chore: update schema (YYYY-MM-DD)`); README не трогается, если схема не изменилась

## Docker

- ENTRYPOINT `["python","-m","ozon_schema_fetcher"]`, CMD `["-o","/schemas/ozon-seller-api-openapi.json"]`: аргументы после имени образа ЗАМЕНЯЮТ CMD целиком — в `docker run` всегда передавать полную пару `-o ...`
- `HOME=/root`: camoufox виснет без HOME или непишущего `$HOME` (camoufox #572/#620); директивы `USER` нет, root упрощает `-v` mount для CI-записи в `schemas/`
- apt-пакеты trixie с суффиксом `t64` (64-bit time_t ABI): `libasound2t64`, `libgtk-3-0t64`, `libatk1.0-0t64`, ...
- Браузер собирается в builder-стадии в `/root/.cache/camoufox` и копируется в runtime; dev-зависимости не попадают в runtime-venv (`--only main`)
