from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import AuditLog
from core.schemas import AuditLogRead

from .dependencies import get_session

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/", response_model=list[AuditLogRead])
async def list_audit_logs(session: AsyncSession = Depends(get_session)) -> list[AuditLog]:
    result = await session.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100))
    return list(result.scalars())
