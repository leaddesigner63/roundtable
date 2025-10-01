"""High level orchestrator for running a round table meeting."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Deque, Dict, Iterable, List

from .exceptions import ValidationError
from .models import AgendaItem, Participant, Topic
from .scheduler import arrange_seating, assign_topics, build_timeline


class RoundTableSession:
    """Encapsulates meeting state, agenda rotation and minutes tracking."""

    def __init__(
        self,
        participants: Iterable[Participant | str],
        topics: Iterable[Topic],
        *,
        start_time: datetime | None = None,
        gap_between_topics: timedelta = timedelta(minutes=5),
    ) -> None:
        self._participants = arrange_seating(list(participants))
        self._topics = list(topics)
        if not self._topics:
            raise ValidationError("Повестка не может быть пустой.")
        self._start_time = start_time or datetime.now().replace(second=0, microsecond=0)
        self._gap = gap_between_topics
        self._timeline: List[AgendaItem] = build_timeline(
            self._start_time, self._topics, gap=self._gap
        )
        self._rotation: Deque[Participant] = deque(self._participants)
        self._assignments: Dict[str, Topic] = assign_topics(self._participants, self._topics)
        self._minutes: Dict[str, str] = {}

    @property
    def participants(self) -> List[Participant]:
        return list(self._participants)

    @property
    def topics(self) -> List[Topic]:
        return list(self._topics)

    @property
    def timeline(self) -> List[AgendaItem]:
        return list(self._timeline)

    @property
    def assignments(self) -> Dict[str, Topic]:
        return dict(self._assignments)

    def current_moderator(self) -> Participant:
        return self._rotation[0]

    def next_topic(self) -> Topic:
        current = self._assignments[self.current_moderator().name]
        return current

    def advance_round(self, steps: int = 1) -> Participant:
        if steps < 0:
            raise ValidationError("Число шагов не может быть отрицательным.")
        self._rotation.rotate(-steps)
        return self._rotation[0]

    def record_minutes(self, topic_title: str, notes: str) -> None:
        if topic_title not in {topic.title for topic in self._topics}:
            raise ValidationError("Тема не найдена в повестке.")
        self._minutes[topic_title] = notes.strip()

    def minutes(self) -> Dict[str, str]:
        return dict(self._minutes)

    def session_overview(self) -> str:
        lines = ["Круглый стол"]
        lines.append("Участники:")
        for participant in self._participants:
            role = f" ({participant.role})" if participant.role else ""
            lines.append(f"- {participant.name}{role}")
        lines.append("\nРаспределение тем:")
        for participant in self._participants:
            topic = self._assignments[participant.name]
            owner = f" (ведущий: {topic.owner})" if topic.owner else ""
            lines.append(f"- {participant.name}: {topic.title}{owner}")
        lines.append("\nХронология:")
        for item in self._timeline:
            lines.append(
                f"- {item.start:%H:%M}–{item.end:%H:%M}: {item.topic.title}"
            )
        if self._minutes:
            lines.append("\nИтоги:")
            for title, text in self._minutes.items():
                lines.append(f"- {title}: {text}")
        return "\n".join(lines)
