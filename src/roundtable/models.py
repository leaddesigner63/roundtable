"""Data models describing participants, topics and agenda items."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Sequence

from .exceptions import ValidationError


@dataclass(slots=True, frozen=True)
class Participant:
    """Represents a meeting participant."""

    name: str
    role: str = "Участник"
    department: str | None = None

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValidationError("Имя участника не может быть пустым.")
        object.__setattr__(self, "name", name)


@dataclass(slots=True, frozen=True)
class Topic:
    """Represents a discussion topic with a planned duration."""

    title: str
    duration: timedelta
    owner: str | None = None
    materials: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        title = self.title.strip()
        if not title:
            raise ValidationError("Название темы не может быть пустым.")
        if self.duration <= timedelta(0):
            raise ValidationError("Продолжительность темы должна быть положительной.")
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "materials", tuple(self.materials))


@dataclass(slots=True, frozen=True)
class AgendaItem:
    """Single item in an agenda timeline."""

    topic: Topic
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValidationError("Время окончания должно быть позже времени начала.")

    def as_dict(self) -> dict[str, str]:
        """Return a serialisable representation useful for reporting."""

        return {
            "topic": self.topic.title,
            "owner": self.topic.owner or "",
            "start": self.start.isoformat(timespec="minutes"),
            "end": self.end.isoformat(timespec="minutes"),
        }


def ensure_unique_participants(participants: Sequence[Participant]) -> List[Participant]:
    """Return a normalised list of unique participants."""

    seen: set[str] = set()
    result: List[Participant] = []
    for participant in participants:
        if participant.name in seen:
            raise ValidationError("Имена участников должны быть уникальными.")
        seen.add(participant.name)
        result.append(participant)
    if not result:
        raise ValidationError("Список участников не может быть пустым.")
    return result
