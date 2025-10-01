from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.base import ProviderAdapter, ProviderRegistry
from core.models import (
    AuthorType,
    ParticipantStatus,
    Session,
    SessionParticipant,
    SessionStatus,
)
from core.services import add_message, increment_round, list_active_participants, update_session_status


@dataclass
class OrchestratorConfig:
    max_rounds: int
    context_token_limit: int
    turn_timeout: int


class RoundTableOrchestrator:
    def __init__(self, registry: ProviderRegistry, config: OrchestratorConfig):
        self.registry = registry
        self.config = config

    async def run(self, db: AsyncSession, session_obj: Session) -> None:
        await update_session_status(db, session_obj, SessionStatus.RUNNING)
        participants = deque(await list_active_participants(db, session_obj.id))
        round_index = session_obj.current_round

        while participants and round_index < self.config.max_rounds:
            round_index += 1
            await increment_round(db, session_obj)
            history = [m async for m in self._iter_messages(db, session_obj)]
            for participant in list(participants):
                if participant.status != ParticipantStatus.ACTIVE:
                    continue
                provider = self.registry.get(participant.provider.type)
                if not provider:
                    participant.status = ParticipantStatus.EXCLUDED
                    continue
                await self._invoke_provider(db, session_obj, participant, provider, history)
                history = [m async for m in self._iter_messages(db, session_obj)]
                await asyncio.sleep(0)
            participants = deque(
                p for p in participants if p.status == ParticipantStatus.ACTIVE
            )
            if not participants:
                break
        final_status = SessionStatus.FINISHED if participants else SessionStatus.STOPPED
        await update_session_status(db, session_obj, final_status)

    async def _invoke_provider(
        self,
        db: AsyncSession,
        session_obj: Session,
        participant: SessionParticipant,
        provider: ProviderAdapter,
        history: Sequence[dict],
    ) -> None:
        try:
            response = await provider.generate_response(
                topic=session_obj.topic,
                history=history,
                personality=participant.personality,
                token_limit=self.config.context_token_limit,
            )
        except Exception as exc:  # pragma: no cover - provider level
            participant.status = ParticipantStatus.EXCLUDED
            await add_message(
                db,
                session_obj=session_obj,
                author_type=AuthorType.SYSTEM,
                author_name="system",
                content=f"Provider {participant.provider.name} failed: {exc}",
            )
            return

        if not response.content:
            participant.status = ParticipantStatus.EXCLUDED
            await add_message(
                db,
                session_obj=session_obj,
                author_type=AuthorType.SYSTEM,
                author_name="system",
                content=f"Provider {participant.provider.name} returned empty response",
            )
            return

        await add_message(
            db,
            session_obj=session_obj,
            author_type=AuthorType.MODEL,
            author_name=participant.personality.title,
            content=response.content,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            cost=response.cost,
        )

    async def _iter_messages(self, db: AsyncSession, session_obj: Session):
        for message in session_obj.messages:
            yield {
                "role": message.author_type,
                "name": message.author_name,
                "content": message.content,
            }
