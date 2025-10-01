from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.db import get_session
from core.models import Personality, Provider, Session, SessionParticipant, Setting, User
from core.security import get_secrets_manager
from orchestrator.service import DialogueOrchestrator, get_setting, set_setting

api_router = APIRouter(prefix="/api")


async def _load_session_with_details(db: AsyncSession, session_id: int) -> Session:
    result = await db.execute(
        select(Session)
        .options(
            selectinload(Session.messages),
            selectinload(Session.participants)
            .selectinload(SessionParticipant.provider),
            selectinload(Session.participants)
            .selectinload(SessionParticipant.personality),
        )
        .where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _session_detail_response(db: AsyncSession, session_id: int) -> SessionDetailResponse:
    session = await _load_session_with_details(db, session_id)
    return SessionDetailResponse.model_validate(session)


class UserCreate(BaseModel):
    telegram_id: int
    username: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    username: str | None


@api_router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_session)) -> User:
    user = await db.get(User, payload.telegram_id)
    if user:
        return user
    user = User(telegram_id=payload.telegram_id, username=payload.username)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


class ProviderBase(BaseModel):
    name: str
    type: str
    api_key: str
    model_id: str
    parameters: dict = Field(default_factory=dict)
    enabled: bool = True
    order_index: int = 0


class ProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    model_id: str
    parameters: dict
    enabled: bool
    order_index: int


@api_router.get("/providers", response_model=List[ProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_session)) -> List[Provider]:
    result = await db.execute(select(Provider).order_by(Provider.order_index))
    return list(result.scalars().all())


@api_router.post("/providers", response_model=ProviderResponse, status_code=201)
async def create_provider(payload: ProviderBase, db: AsyncSession = Depends(get_session)) -> Provider:
    secrets = get_secrets_manager()
    data = payload.model_dump()
    api_key = data.pop("api_key")
    provider = Provider(
        api_key_encrypted=secrets.encrypt(api_key),
        **data,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


@api_router.put("/providers/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: int, payload: ProviderBase, db: AsyncSession = Depends(get_session)) -> Provider:
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    secrets = get_secrets_manager()
    data = payload.model_dump()
    api_key = data.pop("api_key")
    provider.api_key_encrypted = secrets.encrypt(api_key)
    for field, value in data.items():
        setattr(provider, field, value)
    await db.commit()
    await db.refresh(provider)
    return provider


@api_router.delete("/providers/{provider_id}", status_code=204)
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_session)) -> None:
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)
    await db.commit()


class PersonalityBase(BaseModel):
    title: str
    instructions: str
    style: str | None = None


class PersonalityResponse(PersonalityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


@api_router.get("/personalities", response_model=List[PersonalityResponse])
async def list_personalities(db: AsyncSession = Depends(get_session)) -> List[Personality]:
    result = await db.execute(select(Personality).order_by(Personality.title))
    return list(result.scalars().all())


@api_router.post("/personalities", response_model=PersonalityResponse, status_code=201)
async def create_personality(payload: PersonalityBase, db: AsyncSession = Depends(get_session)) -> Personality:
    personality = Personality(**payload.model_dump())
    db.add(personality)
    await db.commit()
    await db.refresh(personality)
    return personality


@api_router.put("/personalities/{personality_id}", response_model=PersonalityResponse)
async def update_personality(personality_id: int, payload: PersonalityBase, db: AsyncSession = Depends(get_session)) -> Personality:
    personality = await db.get(Personality, personality_id)
    if not personality:
        raise HTTPException(status_code=404, detail="Personality not found")
    data = payload.model_dump()
    for field, value in data.items():
        setattr(personality, field, value)
    await db.commit()
    await db.refresh(personality)
    return personality


@api_router.delete("/personalities/{personality_id}", status_code=204)
async def delete_personality(personality_id: int, db: AsyncSession = Depends(get_session)) -> None:
    personality = await db.get(Personality, personality_id)
    if not personality:
        raise HTTPException(status_code=404, detail="Personality not found")
    await db.delete(personality)
    await db.commit()


class SessionCreate(BaseModel):
    user_id: int
    topic: str
    max_rounds: int | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_type: str
    author_name: str
    content: str
    tokens_in: int
    tokens_out: int
    cost: float
    created_at: datetime


class SessionParticipantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    provider_id: int
    personality_id: int
    provider_name: str
    personality_title: str
    order_index: int
    status: str


class SessionDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    topic: str
    status: str
    max_rounds: int
    current_round: int
    created_at: datetime
    finished_at: datetime | None
    messages: list[MessageResponse]
    participants: list[SessionParticipantResponse]


@api_router.post("/sessions", response_model=SessionDetailResponse, status_code=201)
async def create_session_api(payload: SessionCreate, db: AsyncSession = Depends(get_session)) -> SessionDetailResponse:
    orchestrator = DialogueOrchestrator(db)
    session = await orchestrator.create_session(payload.user_id, payload.topic, payload.max_rounds)
    await db.commit()
    return await _session_detail_response(db, session.id)


@api_router.post("/sessions/{session_id}/start", response_model=SessionDetailResponse)
async def start_session_api(session_id: int, db: AsyncSession = Depends(get_session)) -> SessionDetailResponse:
    orchestrator = DialogueOrchestrator(db)
    session = await orchestrator.start_session(session_id)
    await db.commit()
    return await _session_detail_response(db, session.id)


class StopSessionRequest(BaseModel):
    reason: Literal["user", "timeout", "limit", "error"] = "user"


@api_router.post("/sessions/{session_id}/stop", response_model=SessionDetailResponse)
async def stop_session_api(
    session_id: int,
    payload: Optional[StopSessionRequest] = None,
    db: AsyncSession = Depends(get_session),
) -> SessionDetailResponse:
    orchestrator = DialogueOrchestrator(db)
    session = await orchestrator.stop_session(session_id, reason=(payload.reason if payload else "user"))
    await db.commit()
    return await _session_detail_response(db, session.id)


@api_router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_api(session_id: int, db: AsyncSession = Depends(get_session)) -> SessionDetailResponse:
    return await _session_detail_response(db, session_id)


class ParticipantCreate(BaseModel):
    provider_id: int
    personality_id: int
    order_index: int

@api_router.post(
    "/sessions/{session_id}/participants",
    response_model=SessionParticipantResponse,
    status_code=201,
)
async def add_participant(session_id: int, payload: ParticipantCreate, db: AsyncSession = Depends(get_session)) -> SessionParticipant:
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    provider = await db.get(Provider, payload.provider_id)
    personality = await db.get(Personality, payload.personality_id)
    if not provider or not personality:
        raise HTTPException(status_code=400, detail="Invalid provider or personality")
    participant = SessionParticipant(
        session_id=session_id,
        provider_id=payload.provider_id,
        personality_id=payload.personality_id,
        order_index=payload.order_index,
    )
    db.add(participant)
    await db.commit()
    await db.refresh(participant)
    session_with_details = await _load_session_with_details(db, session_id)
    for item in session_with_details.participants:
        if item.id == participant.id:
            return item
    await db.refresh(participant, attribute_names=["provider", "personality"])
    return participant


@api_router.delete("/sessions/{session_id}/participants/{participant_id}", status_code=204)
async def remove_participant(session_id: int, participant_id: int, db: AsyncSession = Depends(get_session)) -> None:
    participant = await db.get(SessionParticipant, participant_id)
    if not participant or participant.session_id != session_id:
        raise HTTPException(status_code=404, detail="Participant not found")
    await db.delete(participant)
    await db.commit()


class SettingUpdate(BaseModel):
    value: str


class SettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: str


@api_router.get("/settings/{key}", response_model=SettingResponse | None)
async def get_setting_api(key: str, db: AsyncSession = Depends(get_session)) -> SettingResponse | None:
    value = await get_setting(db, key)
    if value is None:
        return None
    return SettingResponse(key=key, value=value)


@api_router.put("/settings/{key}", response_model=SettingResponse)
async def set_setting_api(key: str, payload: SettingUpdate, db: AsyncSession = Depends(get_session)) -> SettingResponse:
    await set_setting(db, key, payload.value)
    await db.commit()
    value = await get_setting(db, key)
    return SettingResponse(key=key, value=value or "")
