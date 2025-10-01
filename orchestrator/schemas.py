from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class MessageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_type: str
    author_name: str
    content: str
    tokens_in: int
    tokens_out: int
    cost: float
    created_at: datetime


class SessionParticipantSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_name: str
    personality_title: str
    order_index: int
    status: str


class SessionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    topic: str
    status: str
    created_at: datetime
    finished_at: Optional[datetime]
    max_rounds: int
    current_round: int
    messages: list[MessageSchema] = Field(default_factory=list)
    participants: list[SessionParticipantSchema] = Field(default_factory=list)


class CreateSessionRequest(BaseModel):
    user_id: int
    topic: str
    max_rounds: Optional[int] = None


class StartSessionRequest(BaseModel):
    session_id: int


class StopSessionRequest(BaseModel):
    reason: Literal["user", "timeout", "limit", "error"] = "user"
