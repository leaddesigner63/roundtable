from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import schemas
from core.database import SessionLocal
from core.models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


def get_db():
    async def _get_db():
        async with SessionLocal() as session:
            yield session

    return _get_db


@router.get("", response_model=list[schemas.AuditLogRead])
async def list_audit_logs(db: AsyncSession = Depends(get_db())):
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100))
    return [schemas.AuditLogRead.model_validate(item) for item in result.scalars().all()]
