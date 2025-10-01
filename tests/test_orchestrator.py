from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from pathlib import Path

import pytest

from core.models import Personality, Provider, Session, SessionParticipant, User
from core.security import SecretsManager
from orchestrator.service import DialogueOrchestrator


@dataclass
class DummySettings:
    max_rounds: int = 2
    context_token_limit: int = 2000
    turn_timeout_sec: float = 5.0
    max_session_tokens: int = 10000
    max_cost_per_session: float = 100.0

    @property
    def payment_url(self) -> str:
        return "https://example.com/pay"


class StubAdapter:
    def __init__(self) -> None:
        self.counter = 0

    async def complete(self, prompt: str, context):
        self.counter += 1
        return f"Ответ {self.counter}", {"prompt_tokens": 5, "completion_tokens": 5, "cost": 0.001}


class CostlyAdapter:
    def __init__(self, cost: float = 0.6) -> None:
        self.cost = cost
        self.counter = 0

    async def complete(self, prompt: str, context):
        self.counter += 1
        return (
            f"Очень дорого {self.counter}",
            {"prompt_tokens": 10, "completion_tokens": 10, "cost": self.cost},
        )


class TokenHeavyAdapter:
    async def complete(self, prompt: str, context):
        return "t" * 200, {"prompt_tokens": 200, "completion_tokens": 200, "cost": 0.0}


class SlowAdapter:
    async def complete(self, prompt: str, context):
        await asyncio.sleep(0.05)
        return "медленный ответ", {"prompt_tokens": 1, "completion_tokens": 1, "cost": 0.0}


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
    captured: list[tuple[str, int]] = []

    async def progress(message, round_number: int) -> None:
        captured.append((message.content, round_number))

    await orchestrator.start_session(session.id, progress_callback=progress)
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
    model_messages = [msg for msg in messages if msg.author_type == "model"]
    assert len(captured) == len(model_messages)
    assert all(round_number >= 1 for _, round_number in captured)


@pytest.mark.asyncio
async def test_orchestrator_stops_on_cost_limit(monkeypatch, db_session):
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

    costly_adapter = CostlyAdapter()

    def adapter_factory(provider_type, api_key, model, **params):
        return costly_adapter

    monkeypatch.setattr("orchestrator.service.create_adapter", adapter_factory)

    settings = DummySettings()
    settings.max_cost_per_session = 1.0
    orchestrator = DialogueOrchestrator(db_session, settings=settings, secrets=secrets)

    session = await orchestrator.create_session(user_id=123, topic="Будущее ИИ", max_rounds=3)
    await db_session.commit()

    await orchestrator.start_session(session.id)
    await db_session.commit()

    stored_session = await db_session.get(Session, session.id)
    assert stored_session.status == "stopped"
    assert stored_session.finished_at is not None
    total_cost = sum(msg.cost for msg in stored_session.messages)
    assert total_cost > settings.max_cost_per_session


@pytest.mark.asyncio
async def test_orchestrator_stops_on_token_limit(monkeypatch, db_session):
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

    def adapter_factory(provider_type, api_key, model, **params):
        return TokenHeavyAdapter()

    monkeypatch.setattr("orchestrator.service.create_adapter", adapter_factory)

    settings = DummySettings()
    settings.max_session_tokens = 600
    orchestrator = DialogueOrchestrator(db_session, settings=settings, secrets=secrets)

    session = await orchestrator.create_session(user_id=123, topic="Будущее ИИ", max_rounds=5)
    await db_session.commit()

    await orchestrator.start_session(session.id)
    await db_session.commit()

    stored_session = await db_session.get(Session, session.id)
    assert stored_session.status == "stopped"
    tokens_used = sum(msg.tokens_in + msg.tokens_out for msg in stored_session.messages)
    assert tokens_used > settings.max_session_tokens


@pytest.mark.asyncio
async def test_orchestrator_logs_tokens_and_cost(monkeypatch, db_session):
    log_path = Path("logs/roundtable.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("")

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
    session = await orchestrator.create_session(user_id=123, topic="Будущее ИИ", max_rounds=1)
    await db_session.commit()

    await orchestrator.start_session(session.id)
    await db_session.commit()

    entries = []
    for line in log_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    usage_entries = [entry for entry in entries if entry.get("record", {}).get("message") == "model_message_stored"]
    assert usage_entries, "Expected model_message_stored entry in logs"

    extra = usage_entries[0]["record"].get("extra", {})
    assert extra.get("tokens_in") == 5
    assert extra.get("tokens_out") == 5
    assert extra.get("cost") == pytest.approx(0.001)


@pytest.mark.asyncio
async def test_orchestrator_stops_on_timeout(monkeypatch, db_session):
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

    def adapter_factory(provider_type, api_key, model, **params):
        return SlowAdapter()

    monkeypatch.setattr("orchestrator.service.create_adapter", adapter_factory)

    settings = DummySettings()
    settings.turn_timeout_sec = 0.01
    orchestrator = DialogueOrchestrator(db_session, settings=settings, secrets=secrets)

    session = await orchestrator.create_session(user_id=123, topic="Будущее ИИ", max_rounds=2)
    await db_session.commit()

    await orchestrator.start_session(session.id)
    await db_session.commit()

    stored_session = await db_session.get(Session, session.id)
    assert stored_session.status == "stopped"
    model_messages = [msg for msg in stored_session.messages if msg.author_type == "model"]
    assert not model_messages
