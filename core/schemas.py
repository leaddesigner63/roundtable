from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .models import AuthorType, ParticipantStatus, SessionStatus


class ProviderBase(BaseModel):
    name: str
    type: str
    model_id: str
    parameters: dict[str, Any] | None = None
    enabled: bool = True
    order_index: int = 0


class ProviderCreate(ProviderBase):
    api_key: str


class ProviderUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    api_key: str | None = None
    model_id: str | None = None
    parameters: dict[str, Any] | None = None
    enabled: bool | None = None
    order_index: int | None = None


class ProviderRead(ProviderBase):
    id: int

    class Config:
        from_attributes = True


class PersonalityBase(BaseModel):
    title: str
    instructions: str
    style: str


class PersonalityCreate(PersonalityBase):
    pass


class PersonalityUpdate(BaseModel):
    title: str | None = None
    instructions: str | None = None
    style: str | None = None


class PersonalityRead(PersonalityBase):
    id: int

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    topic: str
    max_rounds: int | None = None


class SessionRead(BaseModel):
    id: int
    topic: str
    status: SessionStatus
    created_at: datetime
    finished_at: datetime | None
    max_rounds: int
    current_round: int

    class Config:
        from_attributes = True


class MessageRead(BaseModel):
    id: int
    author_type: AuthorType
    author_name: str
    content: str
    tokens_in: int | None
    tokens_out: int | None
    cost: float | None
    created_at: datetime

    class Config:
        from_attributes = True


class SessionDetail(SessionRead):
    messages: list[MessageRead]


class SessionParticipantRead(BaseModel):
    id: int
    provider_id: int
    personality_id: int
    order_index: int
    status: ParticipantStatus

    class Config:
        from_attributes = True


class SettingRead(BaseModel):
    key: str
    value: str


class SettingUpdate(BaseModel):
    value: str


class AuditLogRead(BaseModel):
    id: int
    actor: str
    action: str
    meta: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class SessionStartResponse(BaseModel):
    session_id: int
    status: SessionStatus


class ApiError(BaseModel):
    detail: str
