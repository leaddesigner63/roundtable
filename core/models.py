from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class SessionStatus(str, enum.Enum):
    created = "created"
    running = "running"
    finished = "finished"
    stopped = "stopped"
    failed = "failed"


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    topic: Mapped[str] = mapped_column(Text)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status", native_enum=False), default=SessionStatus.created
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_rounds: Mapped[int] = mapped_column(Integer, default=5)
    current_round: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship(back_populates="sessions")
    participants: Mapped[list["SessionParticipant"]] = relationship(back_populates="session", order_by="SessionParticipant.order_index")
    messages: Mapped[list["Message"]] = relationship(back_populates="session", order_by="Message.created_at")


class ParticipantStatus(str, enum.Enum):
    active = "active"
    excluded = "excluded"


class SessionParticipant(Base, TimestampMixin):
    __tablename__ = "session_participants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    personality_id: Mapped[int] = mapped_column(ForeignKey("personalities.id"))
    order_index: Mapped[int] = mapped_column(Integer)
    status: Mapped[ParticipantStatus] = mapped_column(
        Enum(ParticipantStatus, name="participant_status", native_enum=False),
        default=ParticipantStatus.active,
    )

    session: Mapped["Session"] = relationship(back_populates="participants")
    provider: Mapped["Provider"] = relationship(back_populates="session_participants")
    personality: Mapped["Personality"] = relationship(back_populates="session_participants")


class AuthorType(str, enum.Enum):
    user = "user"
    system = "system"
    provider = "provider"


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    author_type: Mapped[AuthorType] = mapped_column(Enum(AuthorType, name="author_type", native_enum=False))
    author_name: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="messages")


class ProviderType(str, enum.Enum):
    openai = "openai"
    deepseek = "deepseek"
    mock = "mock"


class Provider(Base, TimestampMixin):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    type: Mapped[ProviderType] = mapped_column(Enum(ProviderType, name="provider_type", native_enum=False))
    api_key_encrypted: Mapped[str] = mapped_column(Text)
    model_id: Mapped[str] = mapped_column(String(255))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    session_participants: Mapped[list["SessionParticipant"]] = relationship(back_populates="provider")


class Personality(Base, TimestampMixin):
    __tablename__ = "personalities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), unique=True)
    instructions: Mapped[str] = mapped_column(Text)
    style: Mapped[str] = mapped_column(Text)

    session_participants: Mapped[list["SessionParticipant"]] = relationship(back_populates="personality")


class Setting(Base, TimestampMixin):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(255))
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
