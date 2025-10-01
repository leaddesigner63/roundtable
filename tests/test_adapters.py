from __future__ import annotations

import httpx
import pytest

from adapters.deepseek_adapter import DeepSeekAdapter
from adapters.openai_adapter import OpenAIAdapter


class MockResponse:
    def __init__(self, payload: dict, exception: Exception | None = None) -> None:
        self._payload = payload
        self._exception = exception
        self.raise_called = False

    def raise_for_status(self) -> None:
        self.raise_called = True
        if self._exception:
            raise self._exception

    def json(self) -> dict:
        return self._payload


class MockAsyncClient:
    def __init__(
        self,
        response: MockResponse,
        calls: list[dict],
        *args,
        **kwargs,
    ) -> None:
        self._response = response
        self._calls = calls
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self) -> "MockAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None

    async def post(self, url: str, *, headers: dict, json: dict) -> MockResponse:
        self._calls.append({"url": url, "headers": headers, "json": json})
        return self._response


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "adapter_cls",
        "endpoint",
        "pricing",
    ),
    [
        (
            OpenAIAdapter,
            "https://api.openai.com/v1/chat/completions",
            {"prompt": 0.000001, "completion": 0.000002},
        ),
        (
            DeepSeekAdapter,
            "https://api.deepseek.com/chat/completions",
            {"prompt": 0.0000008, "completion": 0.0000016},
        ),
    ],
)
async def test_adapter_complete_success(
    adapter_cls: type[OpenAIAdapter | DeepSeekAdapter],
    endpoint: str,
    pricing: dict[str, float],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []
    created_clients: list[MockAsyncClient] = []
    usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    response_payload = {
        "choices": [{"message": {"content": "Hello world"}}],
        "usage": usage,
    }
    mock_response = MockResponse(response_payload)

    def client_factory(*args, **kwargs) -> MockAsyncClient:
        client = MockAsyncClient(mock_response, calls, *args, **kwargs)
        created_clients.append(client)
        return client

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    adapter = adapter_cls(
        api_key="test-key",
        model="model-x",
        temperature=0.2,
        pricing=pricing,
    )
    context = [{"role": "system", "content": "You are helpful."}]

    choice, metadata = await adapter.complete("Tell me a joke", context)

    assert choice == "Hello world"
    assert metadata == {
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "total_tokens": usage["total_tokens"],
        "cost": pricing["prompt"] * usage["prompt_tokens"]
        + pricing["completion"] * usage["completion_tokens"],
    }

    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == endpoint
    assert call["headers"] == {
        "Authorization": "Bearer test-key",
        "Content-Type": "application/json",
    }
    assert call["json"]["model"] == "model-x"
    assert call["json"]["temperature"] == 0.2
    assert call["json"]["messages"] == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Tell me a joke"},
    ]

    assert created_clients[0].kwargs.get("timeout") == 60
    assert mock_response.raise_called is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "adapter_cls",
    [OpenAIAdapter, DeepSeekAdapter],
)
async def test_adapter_complete_http_error(
    adapter_cls: type[OpenAIAdapter | DeepSeekAdapter],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []
    created_clients: list[MockAsyncClient] = []
    endpoint = (
        "https://api.openai.com/v1/chat/completions"
        if adapter_cls is OpenAIAdapter
        else "https://api.deepseek.com/chat/completions"
    )
    request = httpx.Request("POST", endpoint)
    response = httpx.Response(status_code=500, request=request)
    error = httpx.HTTPStatusError("error", request=request, response=response)
    mock_response = MockResponse({"choices": []}, exception=error)

    def client_factory(*args, **kwargs) -> MockAsyncClient:
        client = MockAsyncClient(mock_response, calls, *args, **kwargs)
        created_clients.append(client)
        return client

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)

    adapter = adapter_cls(api_key="test-key", model="model-x")

    with pytest.raises(httpx.HTTPStatusError):
        await adapter.complete("Hi", [])

    assert len(calls) == 1
    assert created_clients[0].kwargs.get("timeout") == 60
    assert mock_response.raise_called is True
