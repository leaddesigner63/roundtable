PYTHON ?= python

.PHONY: install dev migrate seed lint format test

install:
$(PYTHON) -m pip install -e .[dev]

migrate:
alembic upgrade head

seed:
$(PYTHON) -m core.seed

lint:
ruff check .

format:
ruff check --select I .
black .

test:
pytest

 dev:
uvicorn core.main:app --reload --host 0.0.0.0 --port 8000
