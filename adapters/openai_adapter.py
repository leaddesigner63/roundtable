from __future__ import annotations

from typing import Any

import httpx

from adapters.base import BaseLLMAdapter


class OpenAIAdapter(BaseLLMAdapter):
    name = "openai"

    async def complete(self, prompt: str, context: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
        messages = context + [{"role": "user", "content": prompt}]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.options.get("temperature", 0.7),
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        metadata = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "cost": self._estimate_cost(usage),
        }
        return choice, metadata

    def _estimate_cost(self, usage: dict[str, Any]) -> float:
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        rate = self.options.get("pricing", {"prompt": 0.000001, "completion": 0.000002})
        return prompt_tokens * rate.get("prompt", 0) + completion_tokens * rate.get("completion", 0)
