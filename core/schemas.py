from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from .models import AuthorType, ParticipantStatus, ProviderType, SessionStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProviderBase(ORMModel):
    name: str
    type: ProviderType
    model_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    order_index: int = 0


class ProviderCreate(ProviderBase):
    api_key: str


class ProviderRead(ProviderBase):
    id: int


class PersonalityBase(ORMModel):
    title: str
    instructions: str
    style: str


class PersonalityCreate(PersonalityBase):
    pass


class PersonalityRead(PersonalityBase):
    id: int


class SessionCreate(BaseModel):
    user_id: int
    username: str | None = None
    topic: str
    max_rounds: int | None = None


class MessageRead(ORMModel):
    id: int
    author_type: AuthorType
    author_name: str
    content: str
    created_at: datetime


class ParticipantRead(ORMModel):
    id: int
    provider_id: int
    personality_id: int
    order_index: int
    status: ParticipantStatus


class SessionRead(ORMModel):
    id: int
    topic: str
    status: SessionStatus
    current_round: int
    max_rounds: int
    created_at: datetime
    finished_at: datetime | None
    participants: list[ParticipantRead]
    messages: list[MessageRead]


class SessionStatusRead(ORMModel):
    id: int
    status: SessionStatus
    current_round: int
    max_rounds: int
    finished_at: datetime | None


class SettingRead(ORMModel):
    key: str
    value: str


class SettingUpdate(BaseModel):
    value: str


class AuditLogRead(ORMModel):
    id: int
    actor: str
    action: str
    meta: dict[str, Any]
    created_at: datetime
