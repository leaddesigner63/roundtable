from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.db import get_session
from core.models import Personality, Provider, Session, SessionParticipant, Setting, User
from core.security import get_secrets_manager
from orchestrator.service import DialogueOrchestrator, get_setting, set_setting

api_router = APIRouter(prefix="/api")


class UserCreate(BaseModel):
    telegram_id: int
    username: str | None = None


class UserResponse(BaseModel):
    telegram_id: int
    username: str | None

    class Config:
        orm_mode = True


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
    parameters: dict = {}
    enabled: bool = True
    order_index: int = 0


class ProviderResponse(BaseModel):
    id: int
    name: str
    type: str
    model_id: str
    parameters: dict
    enabled: bool
    order_index: int

    class Config:
        orm_mode = True


@api_router.get("/providers", response_model=List[ProviderResponse])
async def list_providers(db: AsyncSession = Depends(get_session)) -> List[Provider]:
    result = await db.execute(select(Provider))
    return list(result.scalars().all())


@api_router.post("/providers", response_model=ProviderResponse, status_code=201)
async def create_provider(payload: ProviderBase, db: AsyncSession = Depends(get_session)) -> Provider:
    secrets = get_secrets_manager()
    provider = Provider(
        name=payload.name,
        type=payload.type,
        api_key_encrypted=secrets.encrypt(payload.api_key),
        model_id=payload.model_id,
        parameters=payload.parameters,
        enabled=payload.enabled,
        order_index=payload.order_index,
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
    provider.name = payload.name
    provider.type = payload.type
    provider.api_key_encrypted = secrets.encrypt(payload.api_key)
    provider.model_id = payload.model_id
    provider.parameters = payload.parameters
    provider.enabled = payload.enabled
    provider.order_index = payload.order_index
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
    id: int

    class Config:
        orm_mode = True


@api_router.get("/personalities", response_model=List[PersonalityResponse])
async def list_personalities(db: AsyncSession = Depends(get_session)) -> List[Personality]:
    result = await db.execute(select(Personality))
    return list(result.scalars().all())


@api_router.post("/personalities", response_model=PersonalityResponse, status_code=201)
async def create_personality(payload: PersonalityBase, db: AsyncSession = Depends(get_session)) -> Personality:
    personality = Personality(**payload.dict())
    db.add(personality)
    await db.commit()
    await db.refresh(personality)
    return personality


@api_router.put("/personalities/{personality_id}", response_model=PersonalityResponse)
async def update_personality(personality_id: int, payload: PersonalityBase, db: AsyncSession = Depends(get_session)) -> Personality:
    personality = await db.get(Personality, personality_id)
    if not personality:
        raise HTTPException(status_code=404, detail="Personality not found")
    personality.title = payload.title
    personality.instructions = payload.instructions
    personality.style = payload.style
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


class SessionResponse(BaseModel):
    id: int
    user_id: int
    topic: str
    status: str
    max_rounds: int
    current_round: int

    class Config:
        orm_mode = True


@api_router.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session_api(payload: SessionCreate, db: AsyncSession = Depends(get_session)) -> Session:
    orchestrator = DialogueOrchestrator(db)
    session = await orchestrator.create_session(payload.user_id, payload.topic, payload.max_rounds)
    await db.commit()
    await db.refresh(session)
    return session


@api_router.post("/sessions/{session_id}/start", response_model=SessionResponse)
async def start_session_api(session_id: int, db: AsyncSession = Depends(get_session)) -> Session:
    orchestrator = DialogueOrchestrator(db)
    session = await orchestrator.start_session(session_id)
    await db.commit()
    await db.refresh(session)
    return session


@api_router.post("/sessions/{session_id}/stop", response_model=SessionResponse)
async def stop_session_api(session_id: int, db: AsyncSession = Depends(get_session)) -> Session:
    orchestrator = DialogueOrchestrator(db)
    session = await orchestrator.stop_session(session_id)
    await db.commit()
    await db.refresh(session)
    return session


@api_router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_api(session_id: int, db: AsyncSession = Depends(get_session)) -> Session:
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


class ParticipantCreate(BaseModel):
    provider_id: int
    personality_id: int
    order_index: int


class ParticipantResponse(BaseModel):
    id: int
    session_id: int
    provider_id: int
    personality_id: int
    order_index: int
    status: str

    class Config:
        orm_mode = True


@api_router.post("/sessions/{session_id}/participants", response_model=ParticipantResponse, status_code=201)
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
    key: str
    value: str

    class Config:
        orm_mode = True


@api_router.get("/settings/{key}", response_model=SettingResponse | None)
async def get_setting_api(key: str, db: AsyncSession = Depends(get_session)) -> Setting | None:
    value = await get_setting(db, key)
    if value is None:
        return None
    return Setting(key=key, value=value)


@api_router.put("/settings/{key}", response_model=SettingResponse)
async def set_setting_api(key: str, payload: SettingUpdate, db: AsyncSession = Depends(get_session)) -> Setting:
    await set_setting(db, key, payload.value)
    await db.commit()
    value = await get_setting(db, key)
    return Setting(key=key, value=value or "")
