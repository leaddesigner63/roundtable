from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.models import (
    AuthorType,
    Message,
    Personality,
    Provider,
    Session,
    SessionParticipant,
    SessionStatus,
    User,
)
from core.schemas import SessionCreate, SessionRead, SessionStatusRead
from orchestrator.service import DiscussionOrchestrator

from .dependencies import get_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def _ensure_user(session: AsyncSession, user_id: int, username: str | None) -> User:
    user = await session.get(User, user_id)
    if user:
        if username and user.username != username:
            user.username = username
        return user
    user = User(telegram_id=user_id, username=username)
    session.add(user)
    await session.flush()
    return user


@router.post("/", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, session: AsyncSession = Depends(get_session)) -> Session:
    user = await _ensure_user(session, payload.user_id, payload.username)

    providers_result = await session.execute(
        select(Provider).where(Provider.enabled.is_(True)).order_by(Provider.order_index)
    )
    providers = list(providers_result.scalars())
    personalities_result = await session.execute(select(Personality).order_by(Personality.id))
    personalities = list(personalities_result.scalars())
    if not providers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No providers configured")
    if len(personalities) < len(providers):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough personalities configured")

    session_obj = Session(
        user_id=user.telegram_id,
        topic=payload.topic,
        max_rounds=payload.max_rounds or settings.max_rounds,
        status=SessionStatus.created,
    )
    session.add(session_obj)
    await session.flush()

    for index, provider in enumerate(providers):
        personality = personalities[index]
        participant = SessionParticipant(
            session_id=session_obj.id,
            provider_id=provider.id,
            personality_id=personality.id,
            order_index=index,
        )
        session.add(participant)

    system_message = Message(
        session_id=session_obj.id,
        author_type=AuthorType.system,
        author_name="system",
        content=f"Discussion topic: {session_obj.topic}",
    )
    session.add(system_message)
    await session.flush()

    session_obj = await DiscussionOrchestrator(session).load_session(session_obj.id)
    return session_obj


@router.get("/{session_id}", response_model=SessionRead)
async def get_session_detail(session_id: int, session: AsyncSession = Depends(get_session)) -> Session:
    orchestrator = DiscussionOrchestrator(session)
    return await orchestrator.load_session(session_id)


@router.post("/{session_id}/start", response_model=SessionStatusRead)
async def start_session(session_id: int, session: AsyncSession = Depends(get_session)) -> Session:
    orchestrator = DiscussionOrchestrator(session)
    session_obj = await orchestrator.start(session_id)
    return session_obj


@router.post("/{session_id}/stop", response_model=SessionStatusRead)
async def stop_session(session_id: int, session: AsyncSession = Depends(get_session)) -> Session:
    orchestrator = DiscussionOrchestrator(session)
    session_obj = await orchestrator.stop(session_id)
    return session_obj
