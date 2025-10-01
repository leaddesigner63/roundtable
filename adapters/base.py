from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseLLMAdapter(ABC):
    name: str

    def __init__(self, api_key: str, model: str, **kwargs: Any) -> None:
        self.api_key = api_key
        self.model = model
        self.options = kwargs

    @abstractmethod
    async def complete(self, prompt: str, context: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
        """Return generated text and metadata (tokens, cost)."""

    async def healthcheck(self) -> bool:
        return True
