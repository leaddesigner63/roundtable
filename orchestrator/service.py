from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from adapters.registry import create_adapter
from core.config import Settings, get_settings
from core.logging import logger
from core.models import (
    AuditLog,
    Message,
    MessageAuthorType,
    Personality,
    Provider,
    Session,
    SessionParticipant,
    SessionParticipantStatus,
    SessionStatusEnum,
    Setting,
    User,
)
from core.security import SecretsManager, get_secrets_manager
from orchestrator.token_counter import estimate_tokens


class DialogueOrchestrator:
    def __init__(self, db: AsyncSession, settings: Settings | None = None, secrets: SecretsManager | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.secrets = secrets or get_secrets_manager()

    async def ensure_user(self, telegram_id: int, username: str | None = None) -> User:
        user = await self.db.get(User, telegram_id)
        if user:
            if username and user.username != username:
                user.username = username
            return user
        user = User(telegram_id=telegram_id, username=username)
        self.db.add(user)
        await self.db.flush()
        return user

    async def create_session(self, user_id: int, topic: str, max_rounds: int | None = None) -> Session:
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError("User must exist before creating a session")
        session = Session(
            user_id=user_id,
            topic=topic,
            max_rounds=max_rounds or self.settings.max_rounds,
        )
        self.db.add(session)
        await self.db.flush()
        await self._attach_default_participants(session)
        logger.info("Session %s created for user %s", session.id, user_id)
        await self._log_action("system", "session_created", {"session_id": session.id})
        return session

    async def start_session(self, session_id: int) -> Session:
        session = await self._load_session(session_id)
        if not session:
            raise ValueError("Session not found")
        session.status = SessionStatusEnum.RUNNING.value
        await self.db.flush()
        await self._ensure_topic_message(session)
        await self._log_action("system", "session_started", {"session_id": session.id})
        await self._run_dialogue(session)
        return session

    async def stop_session(self, session_id: int, reason: str = "user") -> Session:
        session = await self._load_session(session_id)
        if not session:
            raise ValueError("Session not found")
        session.status = SessionStatusEnum.STOPPED.value
        session.finished_at = datetime.utcnow()
        await self.db.flush()
        await self._log_action("system", "session_stopped", {"session_id": session.id, "reason": reason})
        return session

    async def _load_session(self, session_id: int) -> Session:
        result = await self.db.execute(
            select(Session)
            .options(
                selectinload(Session.participants)
                .selectinload(SessionParticipant.provider),
                selectinload(Session.participants)
                .selectinload(SessionParticipant.personality),
                selectinload(Session.messages),
            )
            .where(Session.id == session_id)
        )
        return result.scalars().first()

    async def _run_dialogue(self, session: Session) -> None:
        participant_cache: Dict[int, Dict[str, str | int]] = {}
        session.current_round = 0

        while session.current_round < session.max_rounds:
            logger.info("Session %s entering round %s", session.id, session.current_round + 1)
            for participant in sorted(session.participants, key=lambda p: p.order_index):
                if participant.status != SessionParticipantStatus.ACTIVE.value:
                    continue
                provider = participant.provider
                personality = participant.personality
                adapter = await self._build_adapter(provider)
                prompt = self._build_prompt(session.topic, personality.instructions, personality.style)
                context_messages = self._build_context(session)
                try:
                    reply, metadata = await adapter.complete(prompt=prompt, context=context_messages)
                except Exception as exc:  # pragma: no cover - network issues
                    logger.exception("Provider %s failed: %s", provider.name, exc)
                    participant.status = SessionParticipantStatus.SUSPENDED.value
                    await self._log_action("system", "participant_failed", {"session_id": session.id, "provider": provider.name})
                    continue

                if not reply.strip():
                    tracker = participant_cache.setdefault(participant.id, {"repeat": 0, "last": ""})
                    tracker["repeat"] = int(tracker.get("repeat", 0)) + 1
                    if tracker["repeat"] >= 2:
                        participant.status = SessionParticipantStatus.REMOVED.value
                        await self._log_action("system", "participant_removed", {"session_id": session.id, "provider": provider.name})
                    continue

                tracker = participant_cache.setdefault(participant.id, {"repeat": 0, "last": ""})
                if tracker.get("last") == reply.strip():
                    tracker["repeat"] = int(tracker.get("repeat", 0)) + 1
                    if tracker["repeat"] >= 2:
                        participant.status = SessionParticipantStatus.REMOVED.value
                        await self._log_action("system", "participant_removed", {"session_id": session.id, "provider": provider.name})
                        continue
                else:
                    tracker["repeat"] = 0
                    tracker["last"] = reply.strip()

                tokens_in = int(metadata.get("prompt_tokens", estimate_tokens(prompt)))
                tokens_out = int(metadata.get("completion_tokens", estimate_tokens(reply)))
                cost = float(metadata.get("cost", 0.0))
                message = Message(
                    session_id=session.id,
                    author_type=MessageAuthorType.MODEL.value,
                    author_name=f"{provider.name} as {personality.title}",
                    content=reply,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost=cost,
                )
                self.db.add(message)
                await self.db.flush()
                session.messages.append(message)
                logger.info(
                    "Session %s message stored from %s | tokens_in=%s tokens_out=%s cost=%.5f",
                    session.id,
                    provider.name,
                    tokens_in,
                    tokens_out,
                    cost,
                )
                await self._log_action(
                    provider.name,
                    "message_posted",
                    {
                        "session_id": session.id,
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "cost": cost,
                    },
                )

                if self._context_exceeds_limit(session):
                    await self._compress_history(session)

            session.current_round += 1
            if not any(p.status == SessionParticipantStatus.ACTIVE.value for p in session.participants):
                logger.info("No active participants remaining for session %s", session.id)
                break

        session.status = SessionStatusEnum.FINISHED.value
        session.finished_at = datetime.utcnow()
        await self._log_action("system", "session_finished", {"session_id": session.id, "rounds": session.current_round})

    async def _build_adapter(self, provider: Provider):
        api_key = self.secrets.decrypt(provider.api_key_encrypted)
        return create_adapter(provider.type, api_key=api_key, model=provider.model_id, **provider.parameters)

    async def _attach_default_participants(self, session: Session) -> None:
        providers = await self._get_active_providers()
        personalities = await self._get_personalities()
        if not providers or not personalities:
            return
        for index, provider in enumerate(providers):
            personality = personalities[index % len(personalities)]
            participant = SessionParticipant(
                session_id=session.id,
                provider_id=provider.id,
                personality_id=personality.id,
                order_index=index,
            )
            self.db.add(participant)
        await self.db.flush()

    def _build_prompt(self, topic: str, instructions: str, style: str | None) -> str:
        prompt = f"Тема обсуждения: {topic}. Инструкции: {instructions}."
        if style:
            prompt += f" Стиль: {style}."
        return prompt

    def _build_context(self, session: Session) -> List[dict[str, str]]:
        context: List[dict[str, str]] = [{"role": "system", "content": f"Topic: {session.topic}"}]
        for message in session.messages:
            role = "assistant" if message.author_type == MessageAuthorType.MODEL.value else "user"
            context.append({"role": role, "content": message.content})
        return context

    def _context_exceeds_limit(self, session: Session) -> bool:
        total_tokens = sum(estimate_tokens(msg.content) for msg in session.messages)
        return total_tokens > self.settings.context_token_limit

    async def _compress_history(self, session: Session) -> None:
        if not session.messages:
            return
        # naive compression: keep last half of messages
        cutoff = len(session.messages) // 2
        to_remove = session.messages[:cutoff]
        for message in to_remove:
            await self.db.execute(update(Message).where(Message.id == message.id).values(content="[compressed]"))
        await self._log_action("system", "history_compressed", {"session_id": session.id, "removed": cutoff})

    async def _log_action(self, actor: str, action: str, meta: dict) -> None:
        log = AuditLog(actor=actor, action=action, meta=meta)
        self.db.add(log)
        await self.db.flush()

    async def _ensure_topic_message(self, session: Session) -> None:
        if any(msg.author_type == MessageAuthorType.USER.value for msg in session.messages):
            return
        topic_message = Message(
            session_id=session.id,
            author_type=MessageAuthorType.USER.value,
            author_name="user",
            content=f"Тема обсуждения: {session.topic}",
            tokens_in=estimate_tokens(session.topic),
            tokens_out=0,
            cost=0.0,
        )
        self.db.add(topic_message)
        await self.db.flush()
        session.messages.append(topic_message)

    async def _get_active_providers(self) -> list[Provider]:
        result = await self.db.execute(select(Provider).where(Provider.enabled.is_(True)).order_by(Provider.order_index))
        return list(result.scalars().all())

    async def _get_personalities(self) -> list[Personality]:
        result = await self.db.execute(select(Personality).order_by(Personality.id))
        return list(result.scalars().all())


async def get_setting(db: AsyncSession, key: str, default: str | None = None) -> str | None:
    setting = await db.get(Setting, key)
    return setting.value if setting else default


async def set_setting(db: AsyncSession, key: str, value: str) -> None:
    setting = await db.get(Setting, key)
    if setting:
        setting.value = value
    else:
        db.add(Setting(key=key, value=value))
    await db.flush()
