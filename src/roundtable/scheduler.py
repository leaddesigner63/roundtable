"""Utilities for arranging seating and building meeting schedules."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Iterable, List, Sequence

from .exceptions import ValidationError
from .models import AgendaItem, Participant, Topic, ensure_unique_participants


def _coerce_participants(participants: Iterable[Participant | str]) -> List[Participant]:
    normalised: List[Participant] = []
    for item in participants:
        if isinstance(item, Participant):
            normalised.append(item)
        else:
            normalised.append(Participant(str(item)))
    return ensure_unique_participants(normalised)


def arrange_seating(
    participants: Sequence[Participant | str],
    *,
    start: int | str | None = None,
    clockwise: bool = True,
) -> List[Participant]:
    """Return an ordered list of participants around the table."""

    seats = deque(_coerce_participants(participants))
    if start is not None:
        if isinstance(start, str):
            names = [p.name for p in seats]
            if start not in names:
                raise ValidationError("Указанный участник не найден в списке.")
            index = names.index(start)
        else:
            index = int(start)
        seats.rotate(-index)
    if not clockwise:
        seats = deque(reversed(seats))
    return list(seats)


def assign_topics(
    participants: Sequence[Participant | str],
    topics: Sequence[Topic],
) -> dict[str, Topic]:
    """Assign topics to participants in a round-robin fashion."""

    if not topics:
        raise ValidationError("Повестка не может быть пустой.")
    seats = arrange_seating(participants)
    assignments: dict[str, Topic] = {}
    for index, participant in enumerate(seats):
        assignments[participant.name] = topics[index % len(topics)]
    return assignments


def build_timeline(
    start_time: datetime,
    topics: Sequence[Topic],
    *,
    gap: timedelta = timedelta(minutes=0),
) -> List[AgendaItem]:
    """Construct a chronological agenda timeline."""

    if not topics:
        raise ValidationError("Повестка не может быть пустой.")

    items: List[AgendaItem] = []
    cursor = start_time
    for topic in topics:
        end_time = cursor + topic.duration
        items.append(AgendaItem(topic=topic, start=cursor, end=end_time))
        cursor = end_time + gap
    return items
