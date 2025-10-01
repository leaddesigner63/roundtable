# Отчёт о соответствии требованиям ТЗ

## Итоговая оценка
Текущая реализация покрывает лишь часть требований: базовые модели данных, API-эндпоинты и тесты присутствуют, однако критичные сценарии (функционал Telegram-бота, полноценная админка, оркестрация с таймаутами и историей, Docker-сборка и др.) реализованы не полностью. Следовательно, продукт не соответствует ТЗ.

## Детальные наблюдения

### Стек
| Требование | Статус | Примечание |
| --- | --- | --- |
| FastAPI, aiogram 3, SQLAlchemy 2.x, Jinja2, Celery/Redis, pytest перечислены в проекте | ✅ | Зависимости перечислены в `pyproject.toml`, покрывая требования по стеку и тестовым инструментам.【F:docs/requirements.md†L6-L18】【F:pyproject.toml†L6-L49】 |
| Docker + docker-compose | ❌ | В `docker-compose.yml` сервисы собираются из корня (`build: .`), но в репозитории отсутствует `Dockerfile`, поэтому сборка невозможна.【F:docs/requirements.md†L14-L16】【F:docker-compose.yml†L1-L33】【216d27†L1-L2】 |

### Функционал Telegram-бота
| Требование | Статус | Примечание |
| --- | --- | --- |
| Кнопки и команды `/new`, `/stop`, `/donate` | ✅ | Клавиатура и хендлеры зарегистрированы в боте.【F:docs/requirements.md†L19-L25】【F:bot/keyboards.py†L1-L15】【F:bot/handlers.py†L17-L81】 |
| Сценарий нового обсуждения с поочерёдными ответами и показом истории пользователю | ❌ | После запуска сессии бот отправляет лишь итоговый статус, не транслируя ответы моделей пользователю.【F:docs/requirements.md†L25-L31】【F:bot/handlers.py†L55-L62】 |
| Возможность остановить диалог в любой момент | ❌ | Состояние с `active_session_id` очищается сразу после запуска сессии, поэтому хендлер `/stop` не сможет остановить уже идущий диалог.【F:docs/requirements.md†L31-L31】【F:bot/handlers.py†L57-L75】 |
| Кнопка «Отблагодарить создателя» открывает ссылку | ✅ | Команда `/donate` отправляет `PAYMENT_URL` из настроек.【F:docs/requirements.md†L19-L25】【F:bot/handlers.py†L78-L81】 |

### Оркестрация диалога
| Требование | Статус | Примечание |
| --- | --- | --- |
| Очерёдность моделей, использование темы и истории, защита от повторов | ✅ | `_run_dialogue` перебирает участников в порядке `order_index`, формирует контекст и исключает повторяющихся участников.【F:docs/requirements.md†L33-L39】【F:orchestrator/service.py†L98-L170】 |
| Стоп-условия: команда пользователя, MAX_ROUNDS, таймаут, лимиты токенов/стоимости | ⚠️ | Реализована лишь проверка `max_rounds` и частичное сжатие контекста; нет обработки остановки по команде, таймаута или стоимости/лимитов токенов.【F:docs/requirements.md†L35-L38】【F:orchestrator/service.py†L98-L176】 |
| Контроль токенов и стоимости, сжатие контекста | ⚠️ | Токены/стоимость сохраняются в сообщениях и аудит-логе, но лог-файл не содержит этих данных; сжатие истории примитивно и не учитывает лимит стоимости.【F:docs/requirements.md†L37-L39】【F:orchestrator/service.py†L139-L167】【F:core/logging.py†L1-L5】 |

### Админ-панель
| Требование | Статус | Примечание |
| --- | --- | --- |
| CRUD для провайдеров, персоналий, управление сессиями и настройками | ❌ | HTML-шаблоны показывают только таблицы без форм и действий; эндпоинты FastAPI тоже отсутствуют для HTML-форм. История сессий и принудительная остановка недоступны из UI.【F:docs/requirements.md†L41-L45】【F:admin/main.py†L26-L65】【F:admin/templates/providers.html†L1-L28】【F:admin/templates/personalities.html†L1-L21】【F:admin/templates/sessions.html†L1-L28】【F:admin/templates/settings.html†L1-L20】 |
| Хранение ключей в БД зашифровано (Fernet) | ✅ | Провайдеры сохраняют `api_key_encrypted`, а `SecretsManager` использует Fernet для шифрования/дешифрования.【F:docs/requirements.md†L45-L46】【F:core/models.py†L37-L51】【F:core/security.py†L7-L22】 |
| Аудит-лог действий | ✅ | Оркестратор пишет события в таблицу `audit_logs` через `_log_action`.【F:docs/requirements.md†L45-L47】【F:orchestrator/service.py†L154-L176】【F:core/models.py†L145-L152】 |

### API
| Требование | Статус | Примечание |
| --- | --- | --- |
| CRUD для сущностей, запуск/остановка сессий | ✅ | REST-эндпоинты реализованы и используют `DialogueOrchestrator`.【F:docs/requirements.md†L49-L55】【F:admin/api.py†L32-L218】 |
| `GET /api/sessions/{id}` возвращает статус и историю | ❌ | Эндпоинт отдаёт только поля сессии без списка сообщений, поэтому история диалога недоступна.【F:docs/requirements.md†L53-L53】【F:admin/api.py†L213-L218】 |
| Админка на HTML | ⚠️ | Есть базовые шаблоны и маршруты, но без форм и интерактивного управления, что не соответствует требуемым CRUD-возможностям (см. раздел Админ-панель).【F:docs/requirements.md†L54-L55】【F:admin/main.py†L26-L65】 |

### Структура данных и миграции
| Требование | Статус | Примечание |
| --- | --- | --- |
| Таблицы и поля согласно ТЗ | ✅ | SQLAlchemy-модели и Alembic-миграция повторяют структуру `users`, `sessions`, `session_participants`, `messages`, `providers`, `personalities`, `settings`, `audit_logs`.【F:docs/requirements.md†L57-L65】【F:core/models.py†L27-L152】【F:migrations/versions/0001_initial.py†L10-L87】 |

### Переменные окружения
| Требование | Статус | Примечание |
| --- | --- | --- |
| Набор переменных из .env | ✅ | Шаблон `.env.example` содержит все ключи из ТЗ.【F:docs/requirements.md†L67-L84】【F:.env.example†L1-L16】 |

### Тестирование
| Требование | Статус | Примечание |
| --- | --- | --- |
| Unit-тесты для оркестратора | ✅ | `tests/test_orchestrator.py` покрывает цикл раундов с заглушкой адаптера.【F:docs/requirements.md†L105-L107】【F:tests/test_orchestrator.py†L13-L70】 |
| Unit-тесты для адаптеров | ❌ | В каталоге `tests/` отсутствуют тесты для адаптеров; покрытие ограничено оркестратором и API.【F:docs/requirements.md†L105-L107】【23e733†L1-L2】 |
| Интеграционные тесты API | ✅ | `tests/test_api.py` выполняет полный сценарий создания сущностей и запуска сессии через HTTPX/ASGI.【F:docs/requirements.md†L105-L108】【F:tests/test_api.py†L31-L73】 |
| E2E сценарий на 2 раунда | ❌ | Интеграционный тест запускает только один раунд (`max_rounds: 1`), что не соответствует требованию о двух раундах.【F:docs/requirements.md†L107-L108】【F:tests/test_api.py†L61-L68】 |

### Запуск и эксплуатационные требования
| Требование | Статус | Примечание |
| --- | --- | --- |
| Makefile и команды запуска | ✅ | В `README.md` и `Makefile` описаны команды `docker-compose up`, `make migrate`, `make dev`, `make worker`, `make bot`.【F:docs/requirements.md†L110-L114】【F:README.md†L12-L19】【F:Makefile†L1-L24】 |
| Первичный сидинг провайдеров/персоналий | ❌ | Скрипты или команды для автоматического создания записей отсутствуют; README упоминает только ручное выполнение без деталей.【F:docs/requirements.md†L112-L114】【F:README.md†L12-L19】 |

### Acceptance criteria
| Пункт | Статус | Примечание |
| --- | --- | --- |
| 1. docker-compose и админка | ⚠️ | Маршруты админки есть, но из-за отсутствия Dockerfile сервис `api` не собирается, админка недоступна через docker-compose.【F:docs/requirements.md†L116-L118】【F:admin/main.py†L15-L65】【216d27†L1-L2】 |
| 2. Настройка ChatGPT/DeepSeek и PAYMENT_URL через админку | ❌ | В HTML-админке нет форм и механизмов сохранения настроек/ключей; можно только просматривать списки.【F:docs/requirements.md†L118-L119】【F:admin/templates/providers.html†L1-L28】【F:admin/templates/settings.html†L1-L20】 |
| 3. Минимум 2 раунда переписки в Telegram | ❌ | Бот не передаёт ответы моделей пользователю, и тесты покрывают лишь один раунд.【F:docs/requirements.md†L118-L121】【F:bot/handlers.py†L55-L62】【F:tests/test_api.py†L61-L68】 |
| 4. Кнопка «Остановить диалог» | ❌ | Из-за очистки состояния `stop` не влияет на уже запущенную сессию.【F:docs/requirements.md†L119-L121】【F:bot/handlers.py†L57-L75】 |
| 5. Кнопка «Отблагодарить создателя» | ✅ | Хендлер возвращает ссылку оплаты.【F:docs/requirements.md†L119-L122】【F:bot/handlers.py†L78-L81】 |
| 6. История сессии в админке | ❌ | HTML-шаблон `sessions.html` показывает лишь метаданные; сообщений нет.【F:docs/requirements.md†L121-L122】【F:admin/templates/sessions.html†L1-L28】 |
| 7. Логи с данными о токенах и стоимости | ❌ | В лог-файл записываются только сообщения без чисел токенов/стоимости; сведения сохраняются лишь в БД (`AuditLog.meta`).【F:docs/requirements.md†L122-L123】【F:core/logging.py†L1-L5】【F:orchestrator/service.py†L154-L166】 |
| 8. Все тесты проходят | ✅ | Наличие тестов соответствует требованию, хотя покрытие неполное (см. замечание выше).【F:docs/requirements.md†L123-L124】【F:tests/test_api.py†L31-L73】 |

