from __future__ import annotations

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from .base import ProviderAdapter, ProviderResponse
from core.models import Personality


class OpenAIAdapter(ProviderAdapter):
    def __init__(self, *, api_key: str, model: str, name: str = "ChatGPT"):
        self.api_key = api_key
        self.model = model
        self.name = name
        self._client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )

    async def generate_response(self, *, topic: str, history, personality: Personality, token_limit: int):
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are participating in a round table discussion on '{topic}'. "
                    f"Personality instructions: {personality.instructions}. Style: {personality.style}."
                ),
            }
        ]
        messages.extend(history)
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max(token_limit // 4, 128),
        }

        async for attempt in AsyncRetrying(
            wait=wait_exponential(multiplier=1, min=1, max=10),
            stop=stop_after_attempt(3),
            retry=retry_if_exception_type(httpx.HTTPError),
        ):
            with attempt:
                response = await self._client.post("/chat/completions", json=payload)
                response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]["message"]
        usage = data.get("usage", {})
        return ProviderResponse(
            content=choice.get("content", ""),
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            cost=None,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
