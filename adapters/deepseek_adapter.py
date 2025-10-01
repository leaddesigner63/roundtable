from __future__ import annotations

import httpx

from .base import ProviderAdapter, ProviderResponse
from core.models import Personality


class DeepSeekAdapter(ProviderAdapter):
    def __init__(self, *, api_key: str, model: str, name: str = "DeepSeek"):
        self.api_key = api_key
        self.model = model
        self.name = name
        self._client = httpx.AsyncClient(
            base_url="https://api.deepseek.com",
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
                    f"Participate in a round table about '{topic}'. Personality: {personality.instructions}. "
                    f"Style: {personality.style}."
                ),
            }
        ]
        messages.extend(history)
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max(token_limit // 4, 128),
        }
        response = await self._client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        usage = data.get("usage", {})
        return ProviderResponse(
            content=message.get("content", ""),
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            cost=None,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
