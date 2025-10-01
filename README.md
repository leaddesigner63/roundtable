# Roundtable

Полностью рабочий инструмент для подготовки и проведения заседаний в формате
круглого стола. Проект реализует модели участников и тем, утилиты для расчёта
рассадки и расписания, а также высокоуровневый класс `RoundTableSession` для
ведения встречи и фиксации итогов.

## Возможности

- валидация данных об участниках и темах (уникальные имена, положительная
  длительность выступлений);
- гибкое построение рассадки с указанием начального участника и направления;
- равномерное распределение тем между участниками;
- генерация временной шкалы заседания с автоматическими паузами;
- управление сессией: текущий модератор, переход между раундами, запись итогов;
- экспорт краткого текстового отчёта по встрече.

## Структура проекта

```
.
├── src/roundtable/        # Исходный код библиотеки
│   ├── __init__.py        # Публичный API пакета
│   ├── core.py            # Совместимость и основные фасады
│   ├── exceptions.py      # Иерархия исключений
│   ├── models.py          # Модели данных (участники, темы, повестка)
│   ├── scheduler.py       # Вспомогательные функции рассадки и таймлайна
│   └── session.py         # Класс RoundTableSession для управления встречей
├── tests/                 # Набор автоматических тестов (pytest)
└── README.md              # Описание проекта и инструкции
```

## Требования

- Python 3.10+
- `pytest` для запуска тестов

## Установка

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
pip install -r requirements.txt  # при наличии дополнительных зависимостей
```

Проект не использует сторонних библиотек, поэтому установка `pytest` достаточно
для запуска тестов. Если вы предпочитаете Poetry, выполните `poetry install`.

## Запуск тестов

```bash
pytest
```

## Пример использования

```python
from datetime import datetime, timedelta

from roundtable import Participant, RoundTableSession, Topic

participants = [
    Participant("Анна", role="Модератор"),
    Participant("Борис", role="Эксперт"),
    Participant("Светлана", role="Аналитик"),
]

topics = [
    Topic("Стратегия", duration=timedelta(minutes=30), owner="Анна"),
    Topic("Маркетинг", duration=timedelta(minutes=20), owner="Борис"),
    Topic("Финансы", duration=timedelta(minutes=25), owner="Светлана"),
]

session = RoundTableSession(participants, topics, start_time=datetime(2024, 5, 20, 10, 0))
print(session.session_overview())
```

## Лицензия

Проект распространяется под лицензией MIT.
