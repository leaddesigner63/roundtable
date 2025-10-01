from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from sqlalchemy import select

from core.models import AuditLog, Personality, Provider, Session, SessionParticipant, User
from core.security import SecretsManager
from orchestrator.service import DialogueOrchestrator


@dataclass
class DummySettings:
    max_rounds: int = 2
    context_token_limit: int = 2000
    turn_timeout_sec: int = 60
    session_tokens_in_limit: int = 60000
    session_tokens_out_limit: int = 60000
    session_cost_limit: float = 100.0

    @property
    def payment_url(self) -> str:
        return "https://example.com/pay"


class StubAdapter:
    def __init__(self) -> None:
        self.counter = 0

    async def complete(self, prompt: str, context):
        self.counter += 1
        return f"Ответ {self.counter}", {"prompt_tokens": 5, "completion_tokens": 5, "cost": 0.001}


class SlowAdapter(StubAdapter):
    async def complete(self, prompt: str, context):
        await asyncio.sleep(1.1)
        return await super().complete(prompt, context)


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


@pytest.mark.asyncio
async def test_orchestrator_stops_on_limits(monkeypatch, db_session):
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
    user = User(telegram_id=456, username="limits")
    db_session.add_all([provider, personality, user])
    await db_session.commit()

    stub_adapter = StubAdapter()

    def adapter_factory(provider_type, api_key, model, **params):
        return stub_adapter

    monkeypatch.setattr("orchestrator.service.create_adapter", adapter_factory)

    settings = DummySettings(
        session_tokens_in_limit=6,
        session_tokens_out_limit=5,
        session_cost_limit=0.001,
    )
    orchestrator = DialogueOrchestrator(db_session, settings=settings, secrets=secrets)
    session = await orchestrator.create_session(user_id=456, topic="Лимиты", max_rounds=3)
    await db_session.commit()

    await orchestrator.start_session(session.id)
    await db_session.commit()

    stored_session = await db_session.get(Session, session.id)
    assert stored_session.status == "stopped"
    audit_logs = (await db_session.execute(select(AuditLog))).scalars().all()
    assert any(log.action == "session_limit_reached" for log in audit_logs)
    limit_log = next(log for log in audit_logs if log.action == "session_limit_reached")
    assert limit_log.meta.get("limit_type") in {"tokens_in", "tokens_out", "cost"}


@pytest.mark.asyncio
async def test_orchestrator_timeout_stops_session(monkeypatch, db_session):
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
    user = User(telegram_id=789, username="timeout")
    db_session.add_all([provider, personality, user])
    await db_session.commit()

    slow_adapter = SlowAdapter()

    def adapter_factory(provider_type, api_key, model, **params):
        return slow_adapter

    monkeypatch.setattr("orchestrator.service.create_adapter", adapter_factory)

    settings = DummySettings(turn_timeout_sec=1)
    orchestrator = DialogueOrchestrator(db_session, settings=settings, secrets=secrets)
    session = await orchestrator.create_session(user_id=789, topic="Таймаут", max_rounds=3)
    await db_session.commit()

    await orchestrator.start_session(session.id)
    await db_session.commit()

    stored_session = await db_session.get(Session, session.id)
    assert stored_session.status == "stopped"
    audit_logs = (await db_session.execute(select(AuditLog))).scalars().all()
    assert any(log.action == "session_timeout" for log in audit_logs)
