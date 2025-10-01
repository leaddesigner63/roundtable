from __future__ import annotations

from .base import ProviderAdapter, ProviderContext


class EchoProvider(ProviderAdapter):
    def __init__(self, name: str):
        self.name = name

    async def generate(self, prompt: str, *, context: ProviderContext) -> str:
        history_text = " | ".join(f"{speaker}:{message}" for speaker, message in context.history[-2:])
        return f"[{self.name}] {context.topic} :: {prompt} :: {history_text}".strip()
