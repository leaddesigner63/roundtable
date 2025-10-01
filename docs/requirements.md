# Техническое задание: Telegram-бот «Круглый стол ИИ»

## Цель
Создать Telegram-бота, который организует поочерёдную дискуссию между несколькими нейросетями (на старте — ChatGPT и DeepSeek) по теме, заданной пользователем. Управление моделями и настройками должно осуществляться через веб-админку.

## Стек
- Python 3.11+
- FastAPI (API и админ-панель)
- aiogram v3 (или python-telegram-bot) для Telegram-бота
- PostgreSQL 14+
- Redis 6+
- Celery или RQ для фоновых задач
- SQLAlchemy 2.x + Alembic
- Jinja2 или FastAPI-Admin для веб-панели
- Docker + docker-compose
- pytest для тестов
- black + ruff для форматирования и линтинга

## Функционал бота
- Кнопки меню:
  1. Новое обсуждение
  2. Остановить диалог
  3. Отблагодарить создателя (открывает платёжную ссылку из конфигурации)
- Команды: `/new`, `/stop`, `/donate`
- Сценарий нового обсуждения:
  - Бот спрашивает тему
  - Создаётся сессия
  - К обсуждению подключаются активные модели в порядке, заданном в админке
  - Ответы генерируются поочерёдно (ChatGPT → DeepSeek → ChatGPT …)
  - Каждая модель учитывает тему, историю диалога и мнения других
- Возможность остановить диалог в любой момент

## Оркестрация диалога
- Модели говорят по очереди, порядок задаётся админкой
- Раунд = цикл по всем моделям
- Стоп-условия: команда пользователя, достижение MAX_ROUNDS, таймаут, превышение лимитов токенов/стоимости
- Контекст: тема + вся история + персоналия модели
- Контроль токенов и стоимости, сжатие контекста при превышении лимитов
- Защита от зацикливания: если модель возвращает пустой/повторяющийся ответ дважды — исключается из сессии

## Админ-панель
- Управление провайдерами моделей (CRUD: название, тип, api_key, model_id, параметры, enabled, порядок)
- Управление персоналиями (CRUD: название, инструкции, стиль)
- Управление сессиями (список, история, принудительная остановка)
- Настройки (MAX_ROUNDS, TURN_TIMEOUT, CONTEXT_TOKEN_LIMIT, PAYMENT_URL)
- Хранение ключей в БД зашифрованно (Fernet)
- Аудит-лог действий

## API (FastAPI)
- `POST /api/sessions` — создать сессию
- `POST /api/sessions/{id}/start` — запустить обсуждение
- `POST /api/sessions/{id}/stop` — остановить
- `GET /api/sessions/{id}` — статус и история
- CRUD эндпоинты для провайдеров, персоналий и настроек
- Админка на HTML (Jinja2 или FastAPI-Admin)

## Структура данных
- users (telegram_id, username, created_at)
- sessions (id, user_id, topic, status, created_at, finished_at, max_rounds, current_round)
- session_participants (session_id, provider_id, personality_id, order_index, status)
- messages (session_id, author_type, author_name, content, tokens_in, tokens_out, cost, created_at)
- providers (id, name, type, api_key, model_id, параметры, enabled, order_index)
- personalities (id, title, instructions, style)
- settings (key, value)
- audit_logs (id, actor, action, meta, created_at)

## Переменные окружения (.env)
```env
TELEGRAM_BOT_TOKEN=...
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=roundtable
POSTGRES_USER=roundtable
POSTGRES_PASSWORD=roundtablepwd
REDIS_URL=redis://redis:6379/0
SECRETS_KEY=base64_fernet_key_here
MAX_ROUNDS=5
TURN_TIMEOUT_SEC=60
CONTEXT_TOKEN_LIMIT=6000
PAYMENT_URL=https://pay.example.com/xyz
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
DEEPSEEK_API_KEY=...
DEEPSEEK_MODEL=deepseek-chat
```

## Репозиторий (структура)
```
/roundtable-ai/
  docker-compose.yml
  Makefile
  .env.example
  README.md
  pyproject.toml
  /bot/
  /orchestrator/
  /adapters/
  /admin/
  /core/
  /worker/
  /migrations/
  /tests/
```

## Тесты
- Unit-тесты для оркестратора и адаптеров (с моками)
- Интеграционные тесты для API
- E2E сценарий: запуск обсуждения на 2 раунда

## Запуск
- `docker-compose up -d`
- `make migrate`
- `make dev`
- Первичный сидинг: создать ChatGPT и DeepSeek провайдеров и персоналии

## Acceptance criteria
1. Запускается docker-compose, доступна админка
2. В админке можно настроить ChatGPT и DeepSeek, PAYMENT_URL
3. В Telegram можно начать обсуждение, получить минимум 2 раунда обмена репликами
4. Кнопка «Остановить диалог» останавливает обсуждение
5. Кнопка «Отблагодарить создателя» открывает ссылку PAYMENT_URL
6. В админке видна история сессии
7. Логи содержат данные о токенах и стоимости
8. Все тесты проходят успешно
