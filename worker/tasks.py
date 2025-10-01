from __future__ import annotations

from celery import shared_task

from core.config import get_settings
from core.db import AsyncSessionLocal
from orchestrator.service import DialogueOrchestrator


@shared_task(name="run_session")
def run_session(session_id: int) -> None:
    settings = get_settings()

    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            orchestrator = DialogueOrchestrator(db, settings=settings)
            await orchestrator.run_session(session_id)
            await db.commit()

    import asyncio

    asyncio.run(_run())
