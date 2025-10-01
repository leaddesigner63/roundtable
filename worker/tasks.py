from __future__ import annotations

import asyncio
from typing import Any

from celery import shared_task

from core.db import AsyncSessionMaker
from orchestrator.service import DiscussionOrchestrator


@shared_task(name="start_session")
def start_session_task(session_id: int) -> dict[str, Any]:
    async def _inner() -> dict[str, Any]:
        async with AsyncSessionMaker() as session:
            orchestrator = DiscussionOrchestrator(session)
            session_obj = await orchestrator.start(session_id)
            return {"session_id": session_obj.id, "status": session_obj.status.value}

    return asyncio.run(_inner())


@shared_task(name="stop_session")
def stop_session_task(session_id: int) -> dict[str, Any]:
    async def _inner() -> dict[str, Any]:
        async with AsyncSessionMaker() as session:
            orchestrator = DiscussionOrchestrator(session)
            session_obj = await orchestrator.stop(session_id)
            return {"session_id": session_obj.id, "status": session_obj.status.value}

    return asyncio.run(_inner())
