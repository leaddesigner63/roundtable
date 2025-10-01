.PHONY: dev migrate lint format test worker bot

export PYTHONPATH := $(PWD)

install:
pip install -e .[dev]

migrate:
alembic upgrade head

revision:
alembic revision --autogenerate -m "auto"

dev:
uvicorn admin.main:app --reload --host 0.0.0.0 --port 8000

worker:
celery -A worker.celery_app worker -l info

bot:
python -m bot.runner

lint:
ruff check .

format:
black .

test:
pytest
