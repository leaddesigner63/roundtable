.PHONY: dev migrate worker lint format test

export PYTHONPATH := $(shell pwd)

install:
poetry install

migrate:
alembic upgrade head

worker:
poetry run celery -A worker.celery_app worker --loglevel=INFO

dev:
poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

lint:
poetry run ruff check .

format:
poetry run black .

format-check:
poetry run black --check .

test:
poetry run pytest
