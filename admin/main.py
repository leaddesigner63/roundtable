from __future__ import annotations

import json

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.api import (
    ProviderBase,
    PersonalityBase,
    SettingUpdate,
    api_router,
    create_personality,
    create_provider,
    delete_personality,
    delete_provider,
    set_setting_api,
    update_personality,
    update_provider,
)
from core.config import get_settings
from core.db import AsyncSessionLocal, get_session
from core.models import Personality, Provider, Session, Setting
from orchestrator.service import DialogueOrchestrator

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


def _parse_bool(value: str | None) -> bool:
    return value not in (None, "", "0", "false", "False", "off")


def _parse_parameters(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Parameters must be a JSON object")
        return parsed
    except json.JSONDecodeError as exc:  # pragma: no cover - validation branch
        raise HTTPException(status_code=400, detail=f"Некорректный JSON параметров: {exc.msg}") from exc
    except ValueError as exc:  # pragma: no cover - validation branch
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/admin/providers")
async def create_provider_form(
    name: str = Form(...),
    type: str = Form(...),
    api_key: str = Form(...),
    model_id: str = Form(...),
    parameters: str | None = Form(default=None),
    enabled: str | None = Form(default=None),
    order_index: int = Form(default=0),
    db: AsyncSession = Depends(get_session),
):
    payload = ProviderBase(
        name=name,
        type=type,
        api_key=api_key,
        model_id=model_id,
        parameters=_parse_parameters(parameters),
        enabled=_parse_bool(enabled),
        order_index=order_index,
    )
    await create_provider(payload, db)
    return RedirectResponse("/admin/providers", status_code=status.HTTP_303_SEE_OTHER)


@app.put("/admin/providers/{provider_id}")
async def update_provider_form(
    provider_id: int,
    name: str = Form(...),
    type: str = Form(...),
    api_key: str = Form(...),
    model_id: str = Form(...),
    parameters: str | None = Form(default=None),
    enabled: str | None = Form(default=None),
    order_index: int = Form(default=0),
    db: AsyncSession = Depends(get_session),
):
    payload = ProviderBase(
        name=name,
        type=type,
        api_key=api_key,
        model_id=model_id,
        parameters=_parse_parameters(parameters),
        enabled=_parse_bool(enabled),
        order_index=order_index,
    )
    await update_provider(provider_id, payload, db)
    return RedirectResponse("/admin/providers", status_code=status.HTTP_303_SEE_OTHER)


@app.delete("/admin/providers/{provider_id}")
async def delete_provider_form(provider_id: int, db: AsyncSession = Depends(get_session)):
    await delete_provider(provider_id, db)
    return RedirectResponse("/admin/providers", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/personalities", response_class=HTMLResponse)
async def admin_personalities(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await db.execute(select(Personality).order_by(Personality.title))
    personalities = result.scalars().all()
    return templates.TemplateResponse("personalities.html", {"request": request, "title": "Персоналии", "personalities": personalities})


@app.post("/admin/personalities")
async def create_personality_form(
    title: str = Form(...),
    instructions: str = Form(...),
    style: str | None = Form(default=None),
    db: AsyncSession = Depends(get_session),
):
    payload = PersonalityBase(title=title, instructions=instructions, style=style or None)
    await create_personality(payload, db)
    return RedirectResponse("/admin/personalities", status_code=status.HTTP_303_SEE_OTHER)


@app.put("/admin/personalities/{personality_id}")
async def update_personality_form(
    personality_id: int,
    title: str = Form(...),
    instructions: str = Form(...),
    style: str | None = Form(default=None),
    db: AsyncSession = Depends(get_session),
):
    payload = PersonalityBase(title=title, instructions=instructions, style=style or None)
    await update_personality(personality_id, payload, db)
    return RedirectResponse("/admin/personalities", status_code=status.HTTP_303_SEE_OTHER)


@app.delete("/admin/personalities/{personality_id}")
async def delete_personality_form(personality_id: int, db: AsyncSession = Depends(get_session)):
    await delete_personality(personality_id, db)
    return RedirectResponse("/admin/personalities", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/sessions", response_class=HTMLResponse)
async def admin_sessions(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await db.execute(select(Session).order_by(Session.created_at.desc()))
    sessions = result.scalars().all()
    return templates.TemplateResponse("sessions.html", {"request": request, "title": "Сессии", "sessions": sessions})


@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await db.execute(select(Setting))
    settings = result.scalars().all()
    return templates.TemplateResponse("settings.html", {"request": request, "title": "Настройки", "settings": settings})


@app.post("/admin/settings")
async def create_setting_form(
    key: str = Form(...),
    value: str = Form(...),
    db: AsyncSession = Depends(get_session),
):
    await set_setting_api(key, SettingUpdate(value=value), db)
    return RedirectResponse("/admin/settings", status_code=status.HTTP_303_SEE_OTHER)


@app.put("/admin/settings/{key}")
async def update_setting_form(
    key: str,
    value: str = Form(...),
    db: AsyncSession = Depends(get_session),
):
    await set_setting_api(key, SettingUpdate(value=value), db)
    return RedirectResponse("/admin/settings", status_code=status.HTTP_303_SEE_OTHER)


@app.delete("/admin/settings/{key}")
async def delete_setting_form(key: str, db: AsyncSession = Depends(get_session)):
    setting = await db.get(Setting, key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    await db.delete(setting)
    await db.commit()
    return RedirectResponse("/admin/settings", status_code=status.HTTP_303_SEE_OTHER)


@app.on_event("startup")
async def startup_event() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        orchestrator = DialogueOrchestrator(session, settings=settings)
        await orchestrator.ensure_user(telegram_id=0, username="system")
