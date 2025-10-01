from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class MessageSchema(BaseModel):
    id: int
    author_type: str
    author_name: str
    content: str
    tokens_in: int
    tokens_out: int
    cost: float
    created_at: datetime

    class Config:
        orm_mode = True


class SessionParticipantSchema(BaseModel):
    id: int
    provider_name: str
    personality_title: str
    order_index: int
    status: str


class SessionSchema(BaseModel):
    id: int
    topic: str
    status: str
    created_at: datetime
    finished_at: Optional[datetime]
    max_rounds: int
    current_round: int
    messages: list[MessageSchema]

    class Config:
        orm_mode = True


class CreateSessionRequest(BaseModel):
    user_id: int
    topic: str
    max_rounds: Optional[int] = None


class StartSessionRequest(BaseModel):
    session_id: int


class StopSessionRequest(BaseModel):
    reason: Literal["user", "timeout", "limit", "error"] = "user"
