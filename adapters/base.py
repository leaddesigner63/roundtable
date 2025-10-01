from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from core.models import Personality


@dataclass
class ProviderResponse:
    content: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost: float | None = None


class ProviderAdapter(Protocol):
    name: str

    async def generate_response(
        self,
        *,
        topic: str,
        history: Sequence[dict],
        personality: Personality,
        token_limit: int,
    ) -> ProviderResponse:
        """Generate response"""


class ProviderRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ProviderAdapter] = {}

    def register(self, provider_type: str, adapter: ProviderAdapter) -> None:
        self._adapters[provider_type] = adapter

    def get(self, provider_type: str) -> ProviderAdapter | None:
        return self._adapters.get(provider_type)
