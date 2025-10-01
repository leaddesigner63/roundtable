from __future__ import annotations

import pytest
from sqlalchemy import select

from core import db as core_db
from core.models import Personality, Provider
from core.security import SecretsManager
from core.seed import seed_initial_data


@pytest.mark.asyncio
async def test_seed_initial_data_creates_defaults(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(core_db.Base.metadata.drop_all)
        await conn.run_sync(core_db.Base.metadata.create_all)
        await conn.run_sync(seed_initial_data)
        await conn.run_sync(seed_initial_data)

    async with core_db.AsyncSessionLocal() as session:
        providers = (await session.execute(select(Provider))).scalars().all()
        personalities = (await session.execute(select(Personality))).scalars().all()

    provider_names = {provider.name for provider in providers}
    assert {"ChatGPT", "DeepSeek"}.issubset(provider_names)
    assert len([p for p in providers if p.name == "ChatGPT"]) == 1
    assert len([p for p in providers if p.name == "DeepSeek"]) == 1

    personality_titles = {personality.title for personality in personalities}
    assert {"ChatGPT — аналитик", "DeepSeek — визионер"}.issubset(personality_titles)

    secrets = SecretsManager()
    decrypted = {
        provider.name: secrets.decrypt(provider.api_key_encrypted) for provider in providers
    }
    assert decrypted["ChatGPT"] == ""
    assert decrypted["DeepSeek"] == ""
