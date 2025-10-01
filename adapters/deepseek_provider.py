from __future__ import annotations

import httpx

from .base import ProviderAdapter, ProviderContext


class DeepSeekProvider(ProviderAdapter):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.name = "deepseek"

    async def generate(self, prompt: str, *, context: ProviderContext) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.deepseek.com/chat",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return ""
            return choices[0]["message"]["content"].strip()
