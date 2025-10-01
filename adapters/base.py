from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProviderContext:
    topic: str
    history: list[tuple[str, str]]
    personality_instructions: str
    personality_style: str


class ProviderAdapter(Protocol):
    name: str

    async def generate(self, prompt: str, *, context: ProviderContext) -> str:
        raise NotImplementedError
