from __future__ import annotations

import asyncio

from sqlalchemy import select

from core.database import SessionLocal
from core.models import Personality, Provider
from core.security import cipher

DEFAULT_PROVIDERS = [
    {
        "name": "ChatGPT",
        "type": "chatgpt",
        "api_key": "",
        "model_id": "gpt-4o-mini",
        "parameters": "{}",
        "order_index": 0,
    },
    {
        "name": "DeepSeek",
        "type": "deepseek",
        "api_key": "",
        "model_id": "deepseek-chat",
        "parameters": "{}",
        "order_index": 1,
    },
]

DEFAULT_PERSONALITIES = [
    {
        "title": "Прагматичный исследователь",
        "instructions": "Давай четкие и практичные ответы.",
        "style": "Структурированный и лаконичный.",
    },
    {
        "title": "Вдохновляющий визионер",
        "instructions": "Стремись к инновационным идеям и синтезу.",
        "style": "Воодушевляющий и образный.",
    },
]


async def seed() -> None:
    async with SessionLocal() as session:
        for provider in DEFAULT_PROVIDERS:
            result = await session.execute(select(Provider).where(Provider.name == provider["name"]))
            if result.scalar_one_or_none():
                continue
            session.add(
                Provider(
                    name=provider["name"],
                    type=provider["type"],
                    api_key=cipher.encrypt(provider["api_key"]),
                    model_id=provider["model_id"],
                    parameters=provider["parameters"],
                    order_index=provider["order_index"],
                )
            )
        for personality in DEFAULT_PERSONALITIES:
            result = await session.execute(
                select(Personality).where(Personality.title == personality["title"])
            )
            if result.scalar_one_or_none():
                continue
            session.add(Personality(**personality))
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
