from __future__ import annotations

import pytest

import httpx

from adapters.deepseek_adapter import DeepSeekAdapter
from adapters.openai_adapter import OpenAIAdapter


class DummyResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:  # pragma: no cover - no error path in tests
        return None

    def json(self) -> dict:
        return self._payload


class DummyClient:
    def __init__(self, response: DummyResponse) -> None:
        self._response = response
        self.posts: list[tuple[str, dict | None, dict | None]] = []

    async def __aenter__(self) -> "DummyClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, *, headers: dict | None = None, json: dict | None = None):
        self.posts.append((url, headers, json))
        return self._response


@pytest.mark.asyncio
async def test_openai_adapter_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    response_payload = {
        "choices": [{"message": {"content": "Привет, мир!"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 6, "total_tokens": 18},
    }
    dummy_response = DummyResponse(response_payload)
    dummy_client = DummyClient(dummy_response)

    captured_kwargs: list[dict] = []

    def client_factory(*args, **kwargs):
        captured_kwargs.append(kwargs)
        return dummy_client

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    adapter = OpenAIAdapter(
        api_key="secret", model="gpt-test", temperature=0.3, pricing={"prompt": 0.001, "completion": 0.002}
    )
    context = [{"role": "system", "content": "Контекст"}]

    result, metadata = await adapter.complete("Скажи привет", context)

    assert result == "Привет, мир!"
    assert metadata == {
        "prompt_tokens": 12,
        "completion_tokens": 6,
        "total_tokens": 18,
        "cost": pytest.approx(0.024),
    }

    assert dummy_client.posts, "HTTP client must be called"
    url, headers, payload = dummy_client.posts[0]
    assert url == "https://api.openai.com/v1/chat/completions"
    assert headers == {
        "Authorization": "Bearer secret",
        "Content-Type": "application/json",
    }
    assert payload["model"] == "gpt-test"
    assert payload["messages"] == context + [{"role": "user", "content": "Скажи привет"}]
    assert payload["temperature"] == 0.3
    assert captured_kwargs == [{"timeout": 60}]


@pytest.mark.asyncio
async def test_deepseek_adapter_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    response_payload = {
        "choices": [{"message": {"content": "Ответ DeepSeek"}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 10, "total_tokens": 18},
    }
    dummy_response = DummyResponse(response_payload)
    dummy_client = DummyClient(dummy_response)

    captured_kwargs: list[dict] = []

    def client_factory(*args, **kwargs):
        captured_kwargs.append(kwargs)
        return dummy_client

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    adapter = DeepSeekAdapter(api_key="deep-secret", model="deep-model")
    context = [{"role": "system", "content": "История"}]

    result, metadata = await adapter.complete("Как дела?", context)

    assert result == "Ответ DeepSeek"
    expected_cost = 8 * 0.0000008 + 10 * 0.0000016
    assert metadata == {
        "prompt_tokens": 8,
        "completion_tokens": 10,
        "total_tokens": 18,
        "cost": pytest.approx(expected_cost),
    }

    assert dummy_client.posts
    url, headers, payload = dummy_client.posts[0]
    assert url == "https://api.deepseek.com/chat/completions"
    assert headers == {
        "Authorization": "Bearer deep-secret",
        "Content-Type": "application/json",
    }
    assert payload["model"] == "deep-model"
    assert payload["messages"] == context + [{"role": "user", "content": "Как дела?"}]
    assert payload["temperature"] == 0.7
    assert captured_kwargs == [{"timeout": 60}]
