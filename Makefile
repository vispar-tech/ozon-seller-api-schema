# Точка входа для локальной работы с репо из корня.
# Полное описание команд — в AGENTS.md и README.md.

.PHONY: help install fetch test lint docker-build docker-fetch

help: ## Показать доступные цели
	@grep -E '^[a-zA-Z_-]+:.*?## ' Makefile | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости (Poetry, включая dev-группу)
	poetry install --with dev

fetch: ## Скачать схему Ozon Seller API → schemas/ozon-seller-api-openapi.json
	poetry run python -m ozon_schema_fetcher -o schemas/ozon-seller-api-openapi.json

test: ## Запустить pytest
	poetry run pytest

lint: ## pre-commit по всем файлам: ruff-format + ruff + mypy
	poetry run pre-commit run -a

docker-build: ## Собрать Docker-образ ozon-schema-fetcher
	docker build -t ozon-schema-fetcher .

docker-fetch: ## Скачать схему через Docker-образ → schemas/
	mkdir -p schemas && docker run --rm -v $(PWD)/schemas:/schemas ozon-schema-fetcher -o /schemas/ozon-seller-api-openapi.json
