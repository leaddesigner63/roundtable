from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AuditLog,
    AuthorType,
    Message,
    ParticipantStatus,
    Personality,
    Provider,
    Session,
    SessionParticipant,
    SessionStatus,
    Setting,
    User,
)


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str | None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if user:
        if username and user.username != username:
            user.username = username
        return user
    user = User(telegram_id=telegram_id, username=username)
    session.add(user)
    await session.flush()
    return user


async def create_session(
    session: AsyncSession,
    *,
    user: User,
    topic: str,
    participants: Iterable[tuple[Provider, Personality]],
    max_rounds: int,
) -> Session:
    session_obj = Session(user=user, topic=topic, max_rounds=max_rounds)
    session.add(session_obj)
    await session.flush()

    for order_index, (provider, personality) in enumerate(participants):
        participant = SessionParticipant(
            session=session_obj,
            provider=provider,
            personality=personality,
            order_index=order_index,
        )
        session.add(participant)
    await session.flush()
    return session_obj


async def list_active_participants(db: AsyncSession, session_id: int) -> list[SessionParticipant]:
    result = await db.execute(
        select(SessionParticipant)
        .where(
            SessionParticipant.session_id == session_id,
            SessionParticipant.status == ParticipantStatus.ACTIVE,
        )
        .order_by(SessionParticipant.order_index)
    )
    return list(result.scalars())


async def add_message(
    db: AsyncSession,
    *,
    session_obj: Session,
    author_type: AuthorType,
    author_name: str,
    content: str,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    cost: float | None = None,
) -> Message:
    message = Message(
        session=session_obj,
        author_type=author_type,
        author_name=author_name,
        content=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost=cost,
    )
    db.add(message)
    await db.flush()
    return message


async def update_session_status(db: AsyncSession, session_obj: Session, status: SessionStatus) -> None:
    session_obj.status = status
    if status in {SessionStatus.FINISHED, SessionStatus.STOPPED, SessionStatus.FAILED}:
        session_obj.finished_at = datetime.utcnow()
    await db.flush()


async def increment_round(db: AsyncSession, session_obj: Session) -> None:
    session_obj.current_round += 1
    await db.flush()


async def log_action(db: AsyncSession, actor: str, action: str, meta: str | None = None) -> None:
    db.add(AuditLog(actor=actor, action=action, meta=meta))
    await db.flush()


async def upsert_setting(db: AsyncSession, key: str, value: str) -> Setting:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    await db.flush()
    return setting


async def get_setting(db: AsyncSession, key: str) -> str | None:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting else None
