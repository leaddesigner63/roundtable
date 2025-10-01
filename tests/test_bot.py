from __future__ import annotations

import pytest

from bot.handlers import stop_dialogue


class DummyState:
    def __init__(self, data: dict | None = None) -> None:
        self._data = data or {}
        self.cleared = False

    async def get_data(self) -> dict:
        return self._data

    async def clear(self) -> None:
        self.cleared = True


class DummyMessage:
    def __init__(self) -> None:
        self.answers: list[str] = []

    async def answer(self, text: str) -> None:
        self.answers.append(text)


@pytest.mark.asyncio
async def test_stop_dialogue_with_active_session(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []

    async def fake_api_post(path: str, payload: dict) -> dict:
        calls.append((path, payload))
        return {"status": "stopped"}

    monkeypatch.setattr("bot.handlers.api_post", fake_api_post)

    message = DummyMessage()
    state = DummyState({"active_session_id": 55})

    await stop_dialogue(message, state)

    assert calls == [("/api/sessions/55/stop", {})]
    assert state.cleared is True
    assert message.answers[-1] == "Диалог остановлен."


@pytest.mark.asyncio
async def test_stop_dialogue_without_active_session(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing_api_post(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("api_post must not be invoked when there is no active session")

    monkeypatch.setattr("bot.handlers.api_post", failing_api_post)

    message = DummyMessage()
    state = DummyState()

    await stop_dialogue(message, state)

    assert message.answers == ["Сейчас нет активного обсуждения."]
    assert state.cleared is False
