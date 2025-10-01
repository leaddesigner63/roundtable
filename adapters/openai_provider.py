from __future__ import annotations

import httpx

from .base import ProviderAdapter, ProviderContext


class OpenAIProvider(ProviderAdapter):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.name = "openai"

    async def generate(self, prompt: str, *, context: ProviderContext) -> str:
        # Simplified placeholder implementation: we call the official OpenAI API if configured.
        # During tests we rely on mocks to avoid network calls.
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "input": prompt,
                    "n": 1,
                },
            )
            response.raise_for_status()
            data = response.json()
            output = data.get("output", [])
            if not output:
                return ""
            return output[0]["content"][0]["text"].strip()
