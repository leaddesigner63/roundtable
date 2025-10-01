# Roundtable AI

Telegram-бот, оркестрирующий обсуждение между несколькими LLM.

## Стек
- Python 3.11
- FastAPI + Jinja2 (админка и API)
- aiogram 3 (бот)
- PostgreSQL, Redis
- Celery

## Запуск
1. Скопируйте `.env.example` в `.env` и заполните значения.
2. `docker-compose up -d`
3. `make migrate`
4. `make dev`
5. `make worker` и `make bot` в отдельных терминалах.

## Тесты
`make test`

Подробности требований см. в [docs/requirements.md](docs/requirements.md).
