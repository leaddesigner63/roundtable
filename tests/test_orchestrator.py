from __future__ import annotations

import pytest

from core.models import (
    AuthorType,
    Message,
    ParticipantStatus,
    Personality,
    Provider,
    ProviderType,
    Session,
    SessionParticipant,
    SessionStatus,
    User,
)
from core.security import cipher
from orchestrator.service import DiscussionOrchestrator


@pytest.mark.asyncio
async def test_orchestrator_runs_rounds(session):
    user = User(telegram_id=1, username="tester")
    session.add(user)

    provider1 = Provider(
        name="Mock-A",
        type=ProviderType.mock,
        api_key_encrypted=cipher.encrypt("secret"),
        model_id="mock",
        enabled=True,
        order_index=0,
    )
    provider2 = Provider(
        name="Mock-B",
        type=ProviderType.mock,
        api_key_encrypted=cipher.encrypt("secret"),
        model_id="mock",
        enabled=True,
        order_index=1,
    )
    session.add_all([provider1, provider2])

    personality1 = Personality(title="Thinker", instructions="Be thoughtful", style="calm")
    personality2 = Personality(title="Rebel", instructions="Challenge ideas", style="bold")
    session.add_all([personality1, personality2])
    await session.flush()

    discussion = Session(
        user_id=user.telegram_id,
        topic="Future of AI",
        max_rounds=2,
        status=SessionStatus.created,
    )
    session.add(discussion)
    await session.flush()

    part1 = SessionParticipant(
        session_id=discussion.id,
        provider_id=provider1.id,
        personality_id=personality1.id,
        order_index=0,
    )
    part2 = SessionParticipant(
        session_id=discussion.id,
        provider_id=provider2.id,
        personality_id=personality2.id,
        order_index=1,
    )
    session.add_all([part1, part2])

    system_message = Message(
        session_id=discussion.id,
        author_type=AuthorType.system,
        author_name="system",
        content="Discussion topic: Future of AI",
    )
    session.add(system_message)
    await session.flush()

    orchestrator = DiscussionOrchestrator(session)
    loaded = await orchestrator.load_session(discussion.id)
    assert len(loaded.participants) == 2

    await orchestrator.start(discussion.id)

    refreshed = await orchestrator.load_session(discussion.id)
    provider_messages = [m for m in refreshed.messages if m.author_type == AuthorType.provider]
    assert len(provider_messages) >= 2
    assert refreshed.status == SessionStatus.finished
    assert all(p.status == ParticipantStatus.active for p in refreshed.participants)
