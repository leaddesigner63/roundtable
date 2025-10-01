from __future__ import annotations

from typing import Any, Dict, Type

from adapters.base import BaseLLMAdapter
from adapters.openai_adapter import OpenAIAdapter
from adapters.deepseek_adapter import DeepSeekAdapter

ADAPTERS: Dict[str, Type[BaseLLMAdapter]] = {
    OpenAIAdapter.name: OpenAIAdapter,
    DeepSeekAdapter.name: DeepSeekAdapter,
}


def create_adapter(provider_type: str, api_key: str, model: str, **params: Any) -> BaseLLMAdapter:
    adapter_cls = ADAPTERS.get(provider_type)
    if not adapter_cls:
        raise ValueError(f"Unknown provider type: {provider_type}")
    return adapter_cls(api_key=api_key, model=model, **params)
