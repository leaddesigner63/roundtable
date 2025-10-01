from __future__ import annotations

import asyncio

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.base import ProviderRegistry
from adapters.deepseek_adapter import DeepSeekAdapter
from adapters.local_echo import EchoAdapter
from adapters.openai_adapter import OpenAIAdapter
from core.config import settings
from core.database import SessionLocal
from core.models import Provider, Session
from core.security import cipher
from orchestrator.engine import OrchestratorConfig, RoundTableOrchestrator


async def _get_registry(db: AsyncSession) -> ProviderRegistry:
    registry = ProviderRegistry()
    result = await db.execute(
        select(Provider).where(Provider.enabled.is_(True)).order_by(Provider.order_index)
    )
    providers = list(result.scalars())
    if not providers:
        registry.register("echo", EchoAdapter(name="Echo"))
        return registry

    for provider in providers:
        api_key = cipher.decrypt(provider.api_key)
        if provider.type == "chatgpt" and api_key:
            registry.register(
                provider.type,
                OpenAIAdapter(api_key=api_key, model=provider.model_id, name=provider.name),
            )
        elif provider.type == "deepseek" and api_key:
            registry.register(
                provider.type,
                DeepSeekAdapter(api_key=api_key, model=provider.model_id, name=provider.name),
            )
        else:
            registry.register(provider.type, EchoAdapter(name=provider.name))
    return registry


async def _run_orchestration(session_id: int) -> None:
    async with SessionLocal() as db:  # type: AsyncSession
        session_obj = await db.get(Session, session_id)
        if not session_obj:
            return
        orchestrator = RoundTableOrchestrator(
            registry=await _get_registry(db),
            config=OrchestratorConfig(
                max_rounds=session_obj.max_rounds or settings.max_rounds,
                context_token_limit=settings.context_token_limit,
                turn_timeout=settings.turn_timeout_sec,
            ),
        )
        await orchestrator.run(db, session_obj)
        await db.commit()


@shared_task(name="worker.tasks.run_session")
def run_session(session_id: int) -> None:
    asyncio.run(_run_orchestration(session_id))


def enqueue_session_run(session_id: int) -> None:
    try:
        run_session.delay(session_id)
    except Exception:  # pragma: no cover - fallback for tests
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            run_session(session_id)
        else:
            loop.create_task(_run_orchestration(session_id))
