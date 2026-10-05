.DEFAULT_GOAL := help
SIZE ?= small
COMPOSE := docker compose

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install Python deps and git hooks
	uv sync
	uv run pre-commit install

up: ## Start the full stack (Postgres, Redpanda, Neo4j, Temporal, MLflow)
	$(COMPOSE) --profile full up -d --wait

up-lite: ## Start core only (Postgres, Redpanda) for machines under 16 GB RAM
	$(COMPOSE) up -d --wait

down: ## Stop all services (keeps data)
	$(COMPOSE) --profile full down

reset: ## Stop everything and DELETE all data volumes
	$(COMPOSE) --profile full down -v

ps: ## Show service status
	$(COMPOSE) --profile full ps

download: ## Download IBM AML dataset from Kaggle (needs ~/.kaggle/kaggle.json)
	./scripts/download_ibm.sh

data-synthetic: ## Prepare small synthetic dataset (no download needed)
	uv run aml-data prepare --source synthetic

data: ## Prepare IBM dataset: make data SIZE=small|medium|full
	uv run aml-data prepare --source ibm --size $(SIZE)

load: ## Load prepared data into Postgres (safe to re-run)
	uv run aml-data load

lint: ## Ruff lint + format check
	uv run ruff check .
	uv run ruff format --check .

typecheck: ## Mypy strict
	uv run mypy

test: ## Unit tests (no Docker needed)
	uv run pytest -m "not integration"

test-int: ## Integration tests (needs make up)
	uv run pytest -m integration

check: lint typecheck test ## Everything CI runs

.PHONY: help install up up-lite down reset ps download data-synthetic data load lint typecheck test test-int check
