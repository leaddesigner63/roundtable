from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SessionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    FINISHED = "finished"
    STOPPED = "stopped"
    FAILED = "failed"


class ParticipantStatus(str, Enum):
    ACTIVE = "active"
    EXCLUDED = "excluded"
    COMPLETED = "completed"


class AuthorType(str, Enum):
    USER = "user"
    MODEL = "model"
    SYSTEM = "system"


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    sessions: Mapped[list[Session]] = relationship(back_populates="user", lazy="selectin")


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    type: Mapped[str] = mapped_column(String(50))
    api_key: Mapped[str]
    model_id: Mapped[str]
    parameters: Mapped[str | None]
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    participants: Mapped[list[SessionParticipant]] = relationship(
        back_populates="provider", lazy="selectin"
    )


class Personality(Base):
    __tablename__ = "personalities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), unique=True)
    instructions: Mapped[str] = mapped_column(Text)
    style: Mapped[str] = mapped_column(Text)

    participants: Mapped[list[SessionParticipant]] = relationship(
        back_populates="personality", lazy="selectin"
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    topic: Mapped[str]
    status: Mapped[SessionStatus] = mapped_column(SQLEnum(SessionStatus), default=SessionStatus.CREATED)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    finished_at: Mapped[datetime | None]
    max_rounds: Mapped[int] = mapped_column(default=5)
    current_round: Mapped[int] = mapped_column(default=0)

    user: Mapped[User] = relationship(back_populates="sessions", lazy="selectin")
    participants: Mapped[list[SessionParticipant]] = relationship(
        back_populates="session", lazy="selectin"
    )
    messages: Mapped[list[Message]] = relationship(
        back_populates="session", order_by="Message.id", lazy="selectin"
    )


class SessionParticipant(Base):
    __tablename__ = "session_participants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    personality_id: Mapped[int] = mapped_column(ForeignKey("personalities.id"))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ParticipantStatus] = mapped_column(
        SQLEnum(ParticipantStatus), default=ParticipantStatus.ACTIVE
    )

    session: Mapped[Session] = relationship(back_populates="participants", lazy="selectin")
    provider: Mapped[Provider] = relationship(back_populates="participants", lazy="selectin")
    personality: Mapped[Personality] = relationship(back_populates="participants", lazy="selectin")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    author_type: Mapped[AuthorType] = mapped_column(SQLEnum(AuthorType))
    author_name: Mapped[str]
    content: Mapped[str] = mapped_column(Text)
    tokens_in: Mapped[int | None]
    tokens_out: Mapped[int | None]
    cost: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    session: Mapped[Session] = relationship(back_populates="messages", lazy="selectin")


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str]


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor: Mapped[str]
    action: Mapped[str]
    meta: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
