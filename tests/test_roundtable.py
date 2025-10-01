import pytest

from roundtable.core import RoundTable, SeatingError, arrange_seating, assign_topics


@pytest.fixture
def participants():
    return ["Артур", "Ланселот", "Гавейн", "Персиваль"]


@pytest.fixture
def agenda():
    return ["Стратегия", "Ресурсы", "Разведка"]


def test_arrange_seating_rotates(participants):
    assert arrange_seating(participants, 2) == [
        "Гавейн",
        "Персиваль",
        "Артур",
        "Ланселот",
    ]


def test_arrange_seating_rejects_duplicates():
    with pytest.raises(SeatingError):
        arrange_seating(["Артур", "Артур"])


def test_assign_topics_round_robin(participants, agenda):
    assignments = assign_topics(participants, agenda)
    assert assignments == {
        "Артур": "Стратегия",
        "Ланселот": "Ресурсы",
        "Гавейн": "Разведка",
        "Персиваль": "Стратегия",
    }


def test_roundtable_overview(participants, agenda):
    table = RoundTable(participants, agenda, current_position=1)
    overview = table.session_overview()
    lines = overview.splitlines()
    assert lines[0] == "Круглый стол:"
    assert any("Ланселот" in line for line in lines)
    assert all(name in overview for name in participants)


def test_roundtable_advance_changes_moderator(participants, agenda):
    table = RoundTable(participants, agenda)
    first = table.moderator()
    table.advance()
    second = table.moderator()
    assert first != second
    assert second == participants[1]


def test_roundtable_requires_agenda(participants):
    with pytest.raises(ValueError):
        RoundTable(participants, [])


def test_assign_topics_requires_topics(participants):
    with pytest.raises(ValueError):
        assign_topics(participants, [])
