# ozon-seller-api-schema

[![Update schema](https://github.com/vispar-tech/ozon-seller-api-schema/actions/workflows/update-schema.yml/badge.svg)](https://github.com/vispar-tech/ozon-seller-api-schema/actions/workflows/update-schema.yml)

Ежедневное зеркало OpenAPI-схемы Ozon Seller API (`docs.ozon.ru/api/seller/swagger.json`).

Схема лежит за Qrator: обычный HTTP-клиент (и браузер, ещё не прошедший JS-челлендж) получает 307-редирект на страницу челленджа, поэтому fetcher гоняет Camoufox (stealth Firefox на Playwright), пытаясь получить тело, которое парсится как JSON. Готовая схема валидируется и коммитится в `schemas/ozon-seller-api-openapi.json`.

## Схема

<!-- SCHEMA-BEGIN -->
| Версия | Paths | Обновлено |
| --- | --- | --- |
| 2.1 | 481 | 2026-09-25 02:52 UTC |
<!-- SCHEMA-END -->

Блок генерируется скриптом: `python scripts/update_readme.py schemas/ozon-seller-api-openapi.json README.md`.

## Быстрое скачивание

Актуальная схема ежедневно коммитится в `schemas/ozon-seller-api-openapi.json` — скачать её можно без клонирования репозитория и установки зависимостей:

```bash
curl -L -o ozon-seller-api-openapi.json \
  https://raw.githubusercontent.com/vispar-tech/ozon-seller-api-schema/main/schemas/ozon-seller-api-openapi.json
```

## Использование

### Локально

Нужны Python 3.14 и Poetry.

| Команда | Что делает |
|---|---|
| `make install` | установка зависимостей (включая dev) |
| `make fetch` | скачать схему в `schemas/` |
| `make test` | pytest |
| `make lint` | pre-commit: ruff-format + ruff + mypy |

### Docker

| Команда | Что делает |
|---|---|
| `make docker-build` | собрать образ `ozon-schema-fetcher` |
| `make docker-fetch` | скачать схему через образ в `schemas/` |

Образ: ENTRYPOINT `python -m ozon_schema_fetcher`, CMD `-o /schemas/ozon-seller-api-openapi.json`. Аргументы после имени образа заменяют CMD, поэтому в `docker run` передают полную пару `-o ...`.

## Структура

- `ozon_schema_fetcher/` — fetcher (навигация и ретраи до JSON), validation, CLI (`__main__.py`)
- `tests/` — pytest
- `scripts/update_readme.py` — обновляет блок схемы в этом README
- `schemas/ozon-seller-api-openapi.json` — зеркало схемы
- `.github/workflows/` — CI и cron-обновление

## CI

- `ci.yml` — каждый push в main и все PR: ruff/mypy/pytest + сборка Docker-образа (gha-кэш слоёв) и smoke-тест образа (`docker run ... --help`).
- `update-schema.yml` — ежедневно в 00:00 UTC и по ручному запуску (`workflow_dispatch`): собирает образ, качает схему, и если файл изменился — обновляет блок схемы в README и коммитит в main (`chore: update schema (YYYY-MM-DD)`). Если схема не изменилась, README не трогается.
