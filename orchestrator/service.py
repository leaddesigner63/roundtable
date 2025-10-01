from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from adapters.base import ProviderContext
from adapters.registry import build_adapter
from core.config import settings
from core.models import (
    AuthorType,
    Message,
    ParticipantStatus,
    Session,
    SessionParticipant,
    SessionStatus,
)
from orchestrator.exceptions import OrchestrationError


class DiscussionOrchestrator:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def load_session(self, session_id: int) -> Session:
        stmt = (
            select(Session)
            .where(Session.id == session_id)
            .options(
                selectinload(Session.participants).selectinload(SessionParticipant.provider),
                selectinload(Session.participants).selectinload(SessionParticipant.personality),
                selectinload(Session.messages),
            )
        )
        result = await self.session.execute(stmt)
        session = result.scalars().unique().one_or_none()
        if not session:
            raise OrchestrationError(f"Session {session_id} not found")
        return session

    async def start(self, session_id: int) -> Session:
        session = await self.load_session(session_id)
        if session.status not in {SessionStatus.created, SessionStatus.stopped}:
            return session

        session.status = SessionStatus.running
        session.current_round = 0
        await self.session.flush()

        await self._run_rounds(session)
        return session

    async def stop(self, session_id: int) -> Session:
        session = await self.load_session(session_id)
        session.status = SessionStatus.stopped
        session.finished_at = datetime.utcnow()
        await self.session.flush()
        return session

    async def _run_rounds(self, session: Session) -> None:
        participants = deque(
            participant
            for participant in sorted(session.participants, key=lambda p: p.order_index)
            if participant.status == ParticipantStatus.active and participant.provider.enabled
        )
        if not participants:
            raise OrchestrationError("No participants configured")

        history: list[tuple[str, str]] = [
            (message.author_name, message.content) for message in session.messages
        ]

        max_rounds = session.max_rounds
        while (
            participants
            and session.current_round < max_rounds
            and session.status == SessionStatus.running
        ):
            session.current_round += 1
            await self.session.flush()

            for _ in range(len(participants)):
                participant = participants[0]
                participants.rotate(-1)
                if participant.status != ParticipantStatus.active:
                    continue
                provider = participant.provider
                if not provider or not provider.enabled:
                    continue
                adapter = build_adapter(provider)
                personality = participant.personality
                prompt = self._build_prompt(session, history, personality.instructions)
                context = ProviderContext(
                    topic=session.topic,
                    history=history,
                    personality_instructions=personality.instructions,
                    personality_style=personality.style,
                )
                try:
                    reply = await asyncio.wait_for(
                        adapter.generate(prompt, context=context),
                        timeout=settings.turn_timeout_sec,
                    )
                except asyncio.TimeoutError:
                    participant.status = ParticipantStatus.excluded
                    continue

                if not reply or self._is_repeat(reply, participant, session):
                    participant.status = ParticipantStatus.excluded
                    continue

                message = Message(
                    session_id=session.id,
                    author_type=AuthorType.provider,
                    author_name=provider.name,
                    content=reply,
                )
                session.messages.append(message)
                history.append((provider.name, reply))

            active = [p for p in participants if p.status == ParticipantStatus.active]
            if not active:
                session.status = SessionStatus.finished
                session.finished_at = datetime.utcnow()

        if session.current_round >= max_rounds:
            session.status = SessionStatus.finished
            session.finished_at = datetime.utcnow()

        await self.session.flush()

    def _is_repeat(self, reply: str, participant: SessionParticipant, session: Session) -> bool:
        last_messages = [m for m in session.messages if m.author_name == participant.provider.name]
        if len(last_messages) < 2:
            return False
        return reply.strip() == last_messages[-1].content.strip() == last_messages[-2].content.strip()

    def _build_prompt(self, session: Session, history: Iterable[tuple[str, str]], instructions: str) -> str:
        history_text = "\n".join(f"{speaker}: {content}" for speaker, content in history[-10:])
        return (
            f"Topic: {session.topic}\n"
            f"Instructions: {instructions}\n"
            f"History:\n{history_text}\n"
            "Continue the discussion with a concise response."
        )
