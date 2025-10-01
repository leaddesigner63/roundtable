# Roundtable

Простой модуль для организации заседаний в формате круглого стола. Включает
утилиты для проверки списка участников, расчёта порядка рассадки и распределения
тем обсуждения.

## Структура проекта

```
.
├── src/roundtable/        # Исходный код библиотеки
├── tests/                 # Набор автоматических тестов (pytest)
└── README.md              # Данный документ
```

## Требования

* Python 3.10+
* [Poetry](https://python-poetry.org/) или стандартный `pip`
* `pytest` для запуска тестов

## Установка зависимостей

Через `pip`:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
pip install pytest
```

Через Poetry:

```bash
poetry install
```

## Запуск тестов

После установки зависимостей выполните:

```bash
pytest
```

## Использование

```python
from roundtable import RoundTable

table = RoundTable(
    participants=["Артур", "Ланселот", "Гавейн", "Персиваль"],
    agenda=["Стратегия", "Ресурсы", "Разведка"],
)

print(table.session_overview())
```
