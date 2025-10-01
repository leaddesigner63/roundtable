from __future__ import annotations

from typing import Callable

from core.models import Provider, ProviderType
from core.security import cipher

from .base import ProviderAdapter
from .deepseek_provider import DeepSeekProvider
from .mock_provider import EchoProvider
from .openai_provider import OpenAIProvider

ProviderFactory = Callable[[Provider], ProviderAdapter]


def build_adapter(provider: Provider) -> ProviderAdapter:
    api_key = cipher.decrypt(provider.api_key_encrypted)
    if provider.type == ProviderType.openai:
        return OpenAIProvider(api_key, provider.model_id)
    if provider.type == ProviderType.deepseek:
        return DeepSeekProvider(api_key, provider.model_id)
    return EchoProvider(provider.name)
