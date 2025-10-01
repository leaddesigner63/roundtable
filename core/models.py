from __future__ import annotations

from datetime import datetime
from typing import Optional

from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db import Base

Base.metadata.clear()


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions: Mapped[list[Session]] = relationship("Session", back_populates="user")


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    type: Mapped[str] = mapped_column(String(50))
    api_key_encrypted: Mapped[str] = mapped_column(String(500))
    model_id: Mapped[str] = mapped_column(String(100))
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    participants: Mapped[list[SessionParticipant]] = relationship("SessionParticipant", back_populates="provider")


class Personality(Base):
    __tablename__ = "personalities"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    instructions: Mapped[str] = mapped_column(Text)
    style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    participants: Mapped[list[SessionParticipant]] = relationship("SessionParticipant", back_populates="personality")


class SessionStatusEnum(str, PyEnum):
    DRAFT = "draft"
    RUNNING = "running"
    FINISHED = "finished"
    STOPPED = "stopped"
    FAILED = "failed"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    topic: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default=SessionStatusEnum.DRAFT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    max_rounds: Mapped[int] = mapped_column(Integer, default=5)
    current_round: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[User] = relationship("User", back_populates="sessions")
    participants: Mapped[list[SessionParticipant]] = relationship(
        "SessionParticipant", back_populates="session", order_by="SessionParticipant.order_index"
    )
    messages: Mapped[list[Message]] = relationship("Message", back_populates="session", order_by="Message.created_at")


class SessionParticipantStatus(str, PyEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class SessionParticipant(Base):
    __tablename__ = "session_participants"
    __table_args__ = (UniqueConstraint("session_id", "order_index"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    personality_id: Mapped[int] = mapped_column(ForeignKey("personalities.id"))
    order_index: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=SessionParticipantStatus.ACTIVE.value)

    session: Mapped[Session] = relationship("Session", back_populates="participants")
    provider: Mapped[Provider] = relationship("Provider", back_populates="participants")
    personality: Mapped[Personality] = relationship("Personality", back_populates="participants")


class MessageAuthorType(str, PyEnum):
    USER = "user"
    MODEL = "model"
    SYSTEM = "system"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    author_type: Mapped[str] = mapped_column(String(20))
    author_name: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped[Session] = relationship("Session", back_populates="messages")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(500))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
