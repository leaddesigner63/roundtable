from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from core.models import Personality, Provider, Session, SessionParticipant, User
from core.security import SecretsManager
from orchestrator.service import DialogueOrchestrator


@dataclass
class DummySettings:
    max_rounds: int = 2
    context_token_limit: int = 2000

    @property
    def payment_url(self) -> str:
        return "https://example.com/pay"


class StubAdapter:
    def __init__(self) -> None:
        self.counter = 0

    async def complete(self, prompt: str, context):
        self.counter += 1
        return f"Ответ {self.counter}", {"prompt_tokens": 5, "completion_tokens": 5, "cost": 0.001}


@pytest.mark.asyncio
async def test_orchestrator_runs_rounds(monkeypatch, db_session):
    secrets = SecretsManager()
    provider = Provider(
        name="OpenAI",
        type="openai",
        api_key_encrypted=secrets.encrypt("key"),
        model_id="gpt",
        parameters={},
        enabled=True,
        order_index=0,
    )
    personality = Personality(title="Expert", instructions="Будь аналитиком", style="Сдержанный")
    user = User(telegram_id=123, username="tester")
    db_session.add_all([provider, personality, user])
    await db_session.commit()

    stub_adapter = StubAdapter()

    def adapter_factory(provider_type, api_key, model, **params):
        return stub_adapter

    monkeypatch.setattr("orchestrator.service.create_adapter", adapter_factory)

    orchestrator = DialogueOrchestrator(db_session, settings=DummySettings(), secrets=secrets)
    session = await orchestrator.create_session(user_id=123, topic="Будущее ИИ", max_rounds=2)
    await db_session.commit()
    await orchestrator.start_session(session.id)
    await db_session.commit()

    stored_session = await db_session.get(Session, session.id)
    assert stored_session.status == "finished"
    participants = await db_session.execute(
        SessionParticipant.__table__.select().where(SessionParticipant.session_id == session.id)
    )
    rows = participants.fetchall()
    assert len(rows) > 0
    messages = stored_session.messages
    assert any(msg.author_name.startswith("OpenAI") for msg in messages)
