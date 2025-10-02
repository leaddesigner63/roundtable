from __future__ import annotations

import pytest

from bot.handlers import start_handler, stop_dialogue


class DummyState:
    def __init__(self, data: dict | None = None) -> None:
        self._data = data or {}
        self.cleared = False

    async def get_data(self) -> dict:
        return self._data

    async def clear(self) -> None:
        self.cleared = True


class DummyMessage:
    def __init__(self, *, user_id: int = 1, username: str | None = None) -> None:
        self.answers: list[dict[str, object]] = []
        self.from_user = type("User", (), {"id": user_id, "username": username})()

    async def answer(self, text: str, reply_markup=None) -> None:
        self.answers.append({"text": text, "reply_markup": reply_markup})


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
    assert message.answers[-1]["text"] == "Диалог остановлен."


@pytest.mark.asyncio
async def test_stop_dialogue_without_active_session(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing_api_post(*args, **kwargs):  # pragma: no cover - should not be called
        raise AssertionError("api_post must not be invoked when there is no active session")

    monkeypatch.setattr("bot.handlers.api_post", failing_api_post)

    message = DummyMessage()
    state = DummyState()

    await stop_dialogue(message, state)

    assert message.answers == [{"text": "Сейчас нет активного обсуждения.", "reply_markup": None}]
    assert state.cleared is False


@pytest.mark.asyncio
async def test_start_handler_registers_user(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict]] = []

    async def fake_api_post(path: str, payload: dict) -> dict:
        calls.append((path, payload))
        return payload

    monkeypatch.setattr("bot.handlers.api_post", fake_api_post)

    large_id = 999_999_999_999
    message = DummyMessage(user_id=large_id, username="big")
    state = DummyState({"active_session_id": 22})

    await start_handler(message, state)

    assert state.cleared is True
    assert calls == [("/api/users", {"telegram_id": large_id, "username": "big"})]
    assert message.answers
    assert message.answers[0]["text"].startswith("Привет!")
