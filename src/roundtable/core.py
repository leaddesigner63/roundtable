"""Core functionality for the roundtable meeting manager.

The goal of this module is to provide simple primitives for organising a
"round table" style meeting.  The API focuses on three pieces of
functionality:

* Validating and arranging seating orders.
* Assigning discussion topics in a fair, round-robin manner.
* Managing the state of an ongoing meeting via the :class:`RoundTable`
  class.

The implementation is intentionally lightweight so it can be used as a
library or as the foundation for a CLI application.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence


class SeatingError(ValueError):
    """Raised when invalid seating configurations are encountered."""


def _normalise_participants(participants: Iterable[str]) -> List[str]:
    normalised = [name.strip() for name in participants if name and name.strip()]
    if not normalised:
        raise SeatingError("Список участников не должен быть пустым.")
    if len(set(normalised)) != len(normalised):
        raise SeatingError("Имена участников должны быть уникальными.")
    return normalised


def arrange_seating(participants: Sequence[str], start_index: int = 0) -> List[str]:
    """Return a seating order beginning at ``start_index``.

    Parameters
    ----------
    participants:
        Имена участников заседания.
    start_index:
        Номер участника, который должен открыть заседание. Поддерживаются
        отрицательные значения и индексы больше размера коллекции — они
        корректируются по модулю длины списка.
    """

    names = _normalise_participants(participants)
    start = start_index % len(names)
    return names[start:] + names[:start]


def assign_topics(participants: Sequence[str], topics: Sequence[str]) -> Dict[str, str]:
    """Назначить темы участникам равномерно по кругу."""

    names = arrange_seating(participants)
    if not topics:
        raise ValueError("Необходимо указать хотя бы одну тему для обсуждения.")

    assignments: Dict[str, str] = {}
    for idx, name in enumerate(names):
        assignments[name] = topics[idx % len(topics)]
    return assignments


@dataclass
class RoundTable:
    """Stateful helper for managing заседание."""

    participants: Sequence[str]
    agenda: Sequence[str]
    current_position: int = 0
    _seating: List[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._seating = arrange_seating(self.participants, self.current_position)
        self._agenda = list(self.agenda)
        if not self._agenda:
            raise ValueError("Повестка дня не должна быть пустой.")

    @property
    def seating(self) -> List[str]:
        """Текущий порядок рассадки."""

        return list(self._seating)

    @property
    def agenda_assignments(self) -> Dict[str, str]:
        """Текущие назначения тем."""

        return assign_topics(self._seating, self._agenda)

    def advance(self, steps: int = 1) -> List[str]:
        """Сместить точку отсчёта по столу и вернуть новое расположение."""

        if steps == 0:
            return self.seating

        self.current_position = (self.current_position + steps) % len(self._seating)
        self._seating = arrange_seating(self._seating, steps)
        return self.seating

    def moderator(self) -> str:
        """Вернуть имя текущего модератора (первого в очереди)."""

        return self._seating[0]

    def session_overview(self) -> str:
        """Предоставить краткое текстовое описание заседания."""

        topics = self.agenda_assignments
        lines = ["Круглый стол:"]
        for name in self._seating:
            lines.append(f"- {name}: {topics[name]}")
        return "\n".join(lines)
