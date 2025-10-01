from __future__ import annotations

from core.models import Personality

from .base import ProviderAdapter, ProviderResponse


class EchoAdapter(ProviderAdapter):
    def __init__(self, name: str = "Echo"):
        self.name = name

    async def generate_response(self, *, topic: str, history, personality: Personality, token_limit: int):
        previous = history[-1]["content"] if history else ""
        text = f"[{personality.title}] reflecting on '{topic}': {previous[-200:]}".strip()
        return ProviderResponse(content=text or f"New thoughts about {topic}")
