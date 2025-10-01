from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Session

from api.dependencies import get_session

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="admin/templates")


@router.get("/sessions")
async def sessions_view(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Session).order_by(Session.created_at.desc()).limit(50))
    sessions = list(result.scalars())
    return templates.TemplateResponse("dashboard.html", {"request": request, "sessions": sessions})
