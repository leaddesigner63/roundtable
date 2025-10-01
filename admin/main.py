from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status as http_status

from admin.api import api_router
from core.config import get_settings
from core.db import AsyncSessionLocal, get_session
from core.models import Personality, Provider, Session, Setting
from orchestrator.service import (
    DialogueOrchestrator,
    SESSION_LIMIT_SETTING_CASTERS,
    set_setting,
)

app = FastAPI(title="Roundtable AI")
app.include_router(api_router)

templates = Jinja2Templates(directory="admin/templates")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    provider_count = await db.scalar(select(func.count()).select_from(Provider))
    personality_count = await db.scalar(select(func.count()).select_from(Personality))
    session_count = await db.scalar(select(func.count()).select_from(Session))
    stats = {
        "providers": provider_count or 0,
        "personalities": personality_count or 0,
        "sessions": session_count or 0,
    }
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": "Админка", "stats": stats})


@app.get("/admin/providers", response_class=HTMLResponse)
async def admin_providers(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await db.execute(select(Provider).order_by(Provider.order_index))
    providers = result.scalars().all()
    return templates.TemplateResponse("providers.html", {"request": request, "title": "Провайдеры", "providers": providers})


@app.get("/admin/personalities", response_class=HTMLResponse)
async def admin_personalities(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await db.execute(select(Personality).order_by(Personality.title))
    personalities = result.scalars().all()
    return templates.TemplateResponse("personalities.html", {"request": request, "title": "Персоналии", "personalities": personalities})


@app.get("/admin/sessions", response_class=HTMLResponse)
async def admin_sessions(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await db.execute(select(Session).order_by(Session.created_at.desc()))
    sessions = result.scalars().all()
    return templates.TemplateResponse("sessions.html", {"request": request, "title": "Сессии", "sessions": sessions})


@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await db.execute(select(Setting))
    settings = result.scalars().all()
    settings_map = {item.key: item.value for item in settings}
    runtime_settings = get_settings()
    limit_values = {
        key: settings_map.get(key, str(getattr(runtime_settings, key)))
        for key in SESSION_LIMIT_SETTING_CASTERS.keys()
    }
    context = {
        "request": request,
        "title": "Настройки",
        "settings": settings,
        "limit_values": limit_values,
    }
    return templates.TemplateResponse("settings.html", context)


@app.post("/admin/settings/limits", response_class=HTMLResponse)
async def update_limits(request: Request, db: AsyncSession = Depends(get_session)) -> RedirectResponse:
    form = await request.form()
    for key in SESSION_LIMIT_SETTING_CASTERS.keys():
        value = form.get(key)
        if value is None or value == "":
            continue
        await set_setting(db, key, value)
    await db.commit()
    return RedirectResponse(url="/admin/settings", status_code=http_status.HTTP_303_SEE_OTHER)


@app.on_event("startup")
async def startup_event() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        orchestrator = DialogueOrchestrator(session, settings=settings)
        await orchestrator.ensure_user(telegram_id=0, username="system")
