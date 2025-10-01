from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .models import AuditLog


async def write_audit_log(session: AsyncSession, actor: str, action: str, meta: dict[str, Any] | None = None) -> None:
    log = AuditLog(actor=actor, action=action, meta=meta or {})
    session.add(log)
    await session.flush()
