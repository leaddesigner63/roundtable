# Roundtable AI Discussion Platform

"Круглый стол ИИ" — платформа, которая запускает поочередные дискуссии между несколькими
моделями ИИ на выбранную пользователем тему. Решение включает Telegram-бота, REST API,
веб-админку и воркер для фоновой оркестрации диалогов.

## Основные компоненты

- **FastAPI** — REST API и административная панель.
- **Telegram-бот** — реализован на aiogram v3.
- **Оркестратор** — фоновая задача, координирующая обмен сообщениями между моделями.
- **Celery** — управление фоновой обработкой.
- **PostgreSQL** — хранилище данных (SQLAlchemy 2.x).
- **Redis** — брокер/кеш для Celery и Telegram FSM.

## Быстрый старт

```bash
cp .env.example .env
docker-compose up -d
make migrate
make seed
make dev
```

После запуска:

- API доступен по адресу `http://localhost:8000`.
- Админ-панель — `http://localhost:8000/admin`.
- Telegram-бот начинает работу после указания токена.

## Тесты

```bash
make test
```

## Линтинг и форматирование

```bash
make lint
make format
```

