from __future__ import annotations

from dataclasses import dataclass

import pytest

from core.models import Personality, Provider, Session, User
from core.security import SecretsManager
from orchestrator.service import DialogueOrchestrator


@dataclass
class E2ESettings:
    max_rounds: int = 2
    context_token_limit: int = 10_000
    turn_timeout_sec: float = 1.0
    max_session_tokens: int = 50_000
    max_cost_per_session: float = 1_000.0


@pytest.mark.asyncio
async def test_e2e_two_round_dialogue(monkeypatch: pytest.MonkeyPatch, db_session) -> None:
    secrets = SecretsManager()

    providers = [
        Provider(
            name="OpenAI",
            type="openai",
            api_key_encrypted=secrets.encrypt("openai-key"),
            model_id="gpt-test",
            parameters={},
            enabled=True,
            order_index=0,
        ),
        Provider(
            name="DeepSeek",
            type="deepseek",
            api_key_encrypted=secrets.encrypt("deepseek-key"),
            model_id="deep-model",
            parameters={},
            enabled=True,
            order_index=1,
        ),
    ]
    personalities = [
        Personality(title="Стратег", instructions="Думай стратегически", style="Формально"),
        Personality(title="Философ", instructions="Будь философом", style="Вдохновенно"),
    ]
    user = User(telegram_id=99, username="e2e")

    db_session.add_all(providers + personalities + [user])
    await db_session.commit()

    class AdapterStub:
        def __init__(self, label: str) -> None:
            self.label = label
            self.calls: list[tuple[str, list[dict[str, str]]]] = []

        async def complete(self, prompt: str, context: list[dict[str, str]]):
            self.calls.append((prompt, context))
            round_no = len(self.calls)
            return f"{self.label} ответ {round_no}", {
                "prompt_tokens": 5,
                "completion_tokens": 7,
                "cost": 0.0,
            }

    adapter_cache: dict[str, AdapterStub] = {}

    def adapter_factory(provider_type: str, api_key: str, model: str, **params):
        return adapter_cache.setdefault(provider_type, AdapterStub(provider_type))

    monkeypatch.setattr("orchestrator.service.create_adapter", adapter_factory)

    orchestrator = DialogueOrchestrator(db_session, settings=E2ESettings(), secrets=secrets)
    session = await orchestrator.create_session(user_id=user.telegram_id, topic="Будущее ИИ", max_rounds=2)
    await db_session.commit()

    progress_rounds: list[int] = []

    async def progress(message, round_number: int) -> None:
        progress_rounds.append(round_number)

    await orchestrator.start_session(session.id, progress_callback=progress)
    await db_session.commit()

    stored_session = await db_session.get(Session, session.id)
    assert stored_session is not None
    assert stored_session.status == "finished"
    assert stored_session.current_round == 2

    model_messages = [msg for msg in stored_session.messages if msg.author_type == "model"]
    assert len(model_messages) == 4
    assert [msg.author_name for msg in model_messages] == [
        "OpenAI as Стратег",
        "DeepSeek as Философ",
        "OpenAI as Стратег",
        "DeepSeek as Философ",
    ]
    assert [msg.content for msg in model_messages] == [
        "openai ответ 1",
        "deepseek ответ 1",
        "openai ответ 2",
        "deepseek ответ 2",
    ]
    assert progress_rounds == [1, 1, 2, 2]
