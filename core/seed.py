from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from core.config import get_settings
from core.models import Personality, Provider, Setting
from core.security import SecretsManager


@dataclass(frozen=True)
class ProviderSeed:
    name: str
    type: str
    model_id: str
    order_index: int
    parameters: dict[str, object]


@dataclass(frozen=True)
class PersonalitySeed:
    title: str
    instructions: str
    style: str | None = None


DEFAULT_PROVIDERS: tuple[ProviderSeed, ...] = (
    ProviderSeed(
        name="ChatGPT",
        type="openai",
        model_id="gpt-4o-mini",
        order_index=0,
        parameters={"temperature": 0.7},
    ),
    ProviderSeed(
        name="DeepSeek",
        type="deepseek",
        model_id="deepseek-chat",
        order_index=1,
        parameters={"temperature": 0.7},
    ),
)

DEFAULT_PERSONALITIES: tuple[PersonalitySeed, ...] = (
    PersonalitySeed(
        title="ChatGPT — аналитик",
        instructions=(
            "Ты — ChatGPT. Анализируй аргументы участников, отвечай структурировано и "
            "делай акцент на практических выводах."
        ),
        style="Спокойный и дружелюбный тон",
    ),
    PersonalitySeed(
        title="DeepSeek — визионер",
        instructions=(
            "Ты — DeepSeek. Предлагай смелые идеи, ставь под сомнение предположения и "
            "делись нестандартными инсайтами."
        ),
        style="Энергичный и вдохновляющий стиль",
    ),
)


def _seed_providers(session: Session, secrets: SecretsManager, seeds: Iterable[ProviderSeed]) -> bool:
    created = False
    encrypted_empty = secrets.encrypt("")
    for seed in seeds:
        exists = session.execute(select(Provider).where(Provider.name == seed.name)).scalar_one_or_none()
        if exists:
            continue
        provider = Provider(
            name=seed.name,
            type=seed.type,
            api_key_encrypted=encrypted_empty,
            model_id=seed.model_id,
            parameters=dict(seed.parameters),
            enabled=True,
            order_index=seed.order_index,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(provider)
        created = True
    return created


def _seed_personalities(session: Session, seeds: Iterable[PersonalitySeed]) -> bool:
    created = False
    for seed in seeds:
        exists = session.execute(select(Personality).where(Personality.title == seed.title)).scalar_one_or_none()
        if exists:
            continue
        personality = Personality(
            title=seed.title,
            instructions=seed.instructions,
            style=seed.style,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(personality)
        created = True
    return created


def _seed_payment_url(session: Session, url: str) -> None:
    existing = session.get(Setting, "PAYMENT_URL")
    if existing:
        return
    session.add(Setting(key="PAYMENT_URL", value=str(url)))


def seed_initial_data(bind: Connection) -> None:
    """Populate providers, personalities and core settings with default records."""

    session = Session(bind=bind)
    try:
        secrets = SecretsManager()
        _seed_providers(session, secrets, DEFAULT_PROVIDERS)
        _seed_personalities(session, DEFAULT_PERSONALITIES)
        settings = get_settings()
        _seed_payment_url(session, settings.payment_url)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
