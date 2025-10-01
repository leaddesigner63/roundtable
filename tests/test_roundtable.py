from datetime import datetime, timedelta

import pytest

from roundtable import (
    AgendaItem,
    Participant,
    RoundTableSession,
    Topic,
    ValidationError,
    arrange_seating,
    assign_topics,
    build_timeline,
)


@pytest.fixture
def sample_participants() -> list[Participant]:
    return [
        Participant("Анна", role="Модератор"),
        Participant("Борис", role="Эксперт"),
        Participant("Светлана", role="Аналитик"),
    ]


@pytest.fixture
def sample_topics() -> list[Topic]:
    return [
        Topic("Стратегия", duration=timedelta(minutes=30), owner="Анна"),
        Topic("Маркетинг", duration=timedelta(minutes=20), owner="Борис"),
        Topic("Финансы", duration=timedelta(minutes=25), owner="Светлана"),
    ]


def test_participant_validation_rejects_duplicates(sample_participants: list[Participant]) -> None:
    with pytest.raises(ValidationError):
        arrange_seating(sample_participants + [Participant("Анна")])


def test_arrange_seating_supports_custom_start(sample_participants: list[Participant]) -> None:
    order = arrange_seating(sample_participants, start="Борис")
    assert [p.name for p in order] == ["Борис", "Светлана", "Анна"]

    reverse = arrange_seating(sample_participants, clockwise=False)
    assert [p.name for p in reverse] == ["Светлана", "Борис", "Анна"]


def test_assign_topics_round_robin(sample_participants: list[Participant]) -> None:
    topics = [
        Topic("A", duration=timedelta(minutes=10)),
        Topic("B", duration=timedelta(minutes=10)),
    ]
    assignments = assign_topics(sample_participants, topics)
    assert assignments["Анна"].title == "A"
    assert assignments["Борис"].title == "B"
    assert assignments["Светлана"].title == "A"


def test_build_timeline_with_gap(sample_topics: list[Topic]) -> None:
    start = datetime(2024, 1, 1, 9, 0)
    timeline = build_timeline(start, sample_topics[:2], gap=timedelta(minutes=5))
    assert isinstance(timeline[0], AgendaItem)
    assert timeline[0].start == start
    assert timeline[0].end == start + timedelta(minutes=30)
    assert timeline[1].start == start + timedelta(minutes=35)
    assert timeline[1].end == start + timedelta(minutes=55)


def test_round_table_session_flow(sample_participants: list[Participant], sample_topics: list[Topic]) -> None:
    start = datetime(2024, 5, 20, 10, 0)
    session = RoundTableSession(sample_participants, sample_topics, start_time=start)

    assert session.current_moderator().name == "Анна"
    assert session.next_topic().title == "Стратегия"

    session.advance_round()
    assert session.current_moderator().name == "Борис"

    session.record_minutes("Стратегия", "Обновить продуктовую линейку")
    assert session.minutes()["Стратегия"] == "Обновить продуктовую линейку"

    overview = session.session_overview()
    assert "Круглый стол" in overview
    assert "Маркетинг" in overview
    assert "10:00" in overview

    with pytest.raises(ValidationError):
        session.record_minutes("Несуществующая тема", "-")

    with pytest.raises(ValidationError):
        session.advance_round(steps=-1)
