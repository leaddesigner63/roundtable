from __future__ import annotations

import json

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from admin.api import api_router
from core.config import get_settings
from core.db import AsyncSessionLocal, get_session
from core.models import Personality, Provider, Session, Setting
from core.security import get_secrets_manager
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
    return templates.TemplateResponse(
        "providers.html",
        {"request": request, "title": "Провайдеры", "providers": providers},
    )


def _provider_form_defaults() -> dict:
    return {
        "name": "",
        "type": "",
        "api_key": "",
        "model_id": "",
        "parameters": "{}",
        "enabled": True,
        "order_index": "0",
    }


def _provider_form_context(
    request: Request,
    *,
    title: str,
    action: str,
    form_data: dict,
    errors: list[str] | None = None,
) -> dict:
    return {
        "request": request,
        "title": title,
        "form": form_data,
        "form_action": action,
        "errors": errors or [],
    }


@app.get("/admin/providers/new", response_class=HTMLResponse)
async def admin_provider_new(request: Request) -> HTMLResponse:
    context = _provider_form_context(
        request,
        title="Новый провайдер",
        action="/admin/providers/new",
        form_data=_provider_form_defaults(),
    )
    return templates.TemplateResponse("provider_form.html", context)


async def _provider_from_form(
    request: Request,
    *,
    existing: Provider | None = None,
) -> tuple[dict, list[str], dict]:
    form = await request.form()
    form_data = {
        "name": form.get("name", "").strip(),
        "type": form.get("type", "").strip(),
        "api_key": form.get("api_key", "").strip(),
        "model_id": form.get("model_id", "").strip(),
        "parameters": form.get("parameters", "").strip() or "{}",
        "enabled": form.get("enabled") == "on",
        "order_index": form.get("order_index", "0").strip() or "0",
    }
    errors: list[str] = []

    if not form_data["name"]:
        errors.append("Название обязательно для заполнения")
    if not form_data["type"]:
        errors.append("Тип обязателен для заполнения")
    if not form_data["model_id"]:
        errors.append("Model ID обязателен для заполнения")
    if not existing and not form_data["api_key"]:
        errors.append("API ключ обязателен для новых провайдеров")

    try:
        order_index = int(form_data["order_index"] or 0)
    except ValueError:
        errors.append("Порядок должен быть числом")
        order_index = 0

    try:
        parameters = json.loads(form_data["parameters"] or "{}")
        if not isinstance(parameters, dict):
            raise ValueError
    except ValueError:
        errors.append("Параметры должны быть корректным JSON-объектом")
        parameters = existing.parameters if existing else {}

    payload = {
        "name": form_data["name"],
        "type": form_data["type"],
        "api_key": form_data["api_key"],
        "model_id": form_data["model_id"],
        "parameters": parameters,
        "enabled": form_data["enabled"],
        "order_index": order_index,
    }

    return form_data, errors, payload


@app.post("/admin/providers/new")
async def admin_provider_create(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    form_data, errors, payload = await _provider_from_form(request)
    if errors:
        context = _provider_form_context(
            request,
            title="Новый провайдер",
            action="/admin/providers/new",
            form_data=form_data,
            errors=errors,
        )
        return templates.TemplateResponse(
            "provider_form.html",
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    secrets = get_secrets_manager()
    provider = Provider(
        name=payload["name"],
        type=payload["type"],
        api_key_encrypted=secrets.encrypt(payload["api_key"]),
        model_id=payload["model_id"],
        parameters=payload["parameters"],
        enabled=payload["enabled"],
        order_index=payload["order_index"],
    )
    db.add(provider)
    await db.commit()
    return RedirectResponse("/admin/providers", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/providers/{provider_id}/edit", response_class=HTMLResponse)
async def admin_provider_edit(
    provider_id: int, request: Request, db: AsyncSession = Depends(get_session)
) -> HTMLResponse:
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    secrets = get_secrets_manager()
    try:
        api_key = secrets.decrypt(provider.api_key_encrypted)
    except ValueError:
        api_key = ""
    form_data = {
        "name": provider.name,
        "type": provider.type,
        "api_key": api_key,
        "model_id": provider.model_id,
        "parameters": json.dumps(provider.parameters or {}, ensure_ascii=False, indent=2),
        "enabled": provider.enabled,
        "order_index": str(provider.order_index),
    }
    context = _provider_form_context(
        request,
        title=f"Редактирование провайдера {provider.name}",
        action=f"/admin/providers/{provider_id}/edit",
        form_data=form_data,
    )
    return templates.TemplateResponse("provider_form.html", context)


@app.post("/admin/providers/{provider_id}/edit")
async def admin_provider_update(
    provider_id: int, request: Request, db: AsyncSession = Depends(get_session)
) -> HTMLResponse:
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    form_data, errors, payload = await _provider_from_form(request, existing=provider)
    if errors:
        context = _provider_form_context(
            request,
            title=f"Редактирование провайдера {provider.name}",
            action=f"/admin/providers/{provider_id}/edit",
            form_data=form_data,
            errors=errors,
        )
        return templates.TemplateResponse(
            "provider_form.html",
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    secrets = get_secrets_manager()
    provider.name = payload["name"]
    provider.type = payload["type"]
    provider.model_id = payload["model_id"]
    provider.parameters = payload["parameters"]
    provider.enabled = payload["enabled"]
    provider.order_index = payload["order_index"]
    if payload["api_key"]:
        provider.api_key_encrypted = secrets.encrypt(payload["api_key"])
    await db.commit()
    return RedirectResponse("/admin/providers", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/admin/providers/{provider_id}/delete")
async def admin_provider_delete(provider_id: int, db: AsyncSession = Depends(get_session)) -> RedirectResponse:
    provider = await db.get(Provider, provider_id)
    if provider:
        await db.delete(provider)
        await db.commit()
    return RedirectResponse("/admin/providers", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/personalities", response_class=HTMLResponse)
async def admin_personalities(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await db.execute(select(Personality).order_by(Personality.title))
    personalities = result.scalars().all()
    return templates.TemplateResponse(
        "personalities.html",
        {
            "request": request,
            "title": "Персоналии",
            "personalities": personalities,
        },
    )


def _personality_form_context(
    request: Request,
    *,
    title: str,
    action: str,
    form_data: dict,
    errors: list[str] | None = None,
) -> dict:
    return {
        "request": request,
        "title": title,
        "form": form_data,
        "form_action": action,
        "errors": errors or [],
    }


@app.get("/admin/personalities/new", response_class=HTMLResponse)
async def admin_personality_new(request: Request) -> HTMLResponse:
    form_data = {"title": "", "instructions": "", "style": ""}
    context = _personality_form_context(
        request,
        title="Новая персоналия",
        action="/admin/personalities/new",
        form_data=form_data,
    )
    return templates.TemplateResponse("personality_form.html", context)


async def _personality_from_form(request: Request) -> tuple[dict, list[str]]:
    form = await request.form()
    form_data = {
        "title": form.get("title", "").strip(),
        "instructions": form.get("instructions", "").strip(),
        "style": form.get("style", "").strip(),
    }
    errors: list[str] = []
    if not form_data["title"]:
        errors.append("Название обязательно для заполнения")
    if not form_data["instructions"]:
        errors.append("Инструкции обязательны для заполнения")
    return form_data, errors


@app.post("/admin/personalities/new")
async def admin_personality_create(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    form_data, errors = await _personality_from_form(request)
    if errors:
        context = _personality_form_context(
            request,
            title="Новая персоналия",
            action="/admin/personalities/new",
            form_data=form_data,
            errors=errors,
        )
        return templates.TemplateResponse(
            "personality_form.html",
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    personality = Personality(**form_data)
    db.add(personality)
    await db.commit()
    return RedirectResponse("/admin/personalities", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/personalities/{personality_id}/edit", response_class=HTMLResponse)
async def admin_personality_edit(
    personality_id: int, request: Request, db: AsyncSession = Depends(get_session)
) -> HTMLResponse:
    personality = await db.get(Personality, personality_id)
    if not personality:
        raise HTTPException(status_code=404, detail="Personality not found")
    form_data = {
        "title": personality.title,
        "instructions": personality.instructions,
        "style": personality.style or "",
    }
    context = _personality_form_context(
        request,
        title=f"Редактирование персоналии {personality.title}",
        action=f"/admin/personalities/{personality_id}/edit",
        form_data=form_data,
    )
    return templates.TemplateResponse("personality_form.html", context)


@app.post("/admin/personalities/{personality_id}/edit")
async def admin_personality_update(
    personality_id: int, request: Request, db: AsyncSession = Depends(get_session)
) -> HTMLResponse:
    personality = await db.get(Personality, personality_id)
    if not personality:
        raise HTTPException(status_code=404, detail="Personality not found")

    form_data, errors = await _personality_from_form(request)
    if errors:
        context = _personality_form_context(
            request,
            title=f"Редактирование персоналии {personality.title}",
            action=f"/admin/personalities/{personality_id}/edit",
            form_data=form_data,
            errors=errors,
        )
        return templates.TemplateResponse(
            "personality_form.html",
            context,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    personality.title = form_data["title"]
    personality.instructions = form_data["instructions"]
    personality.style = form_data["style"] or None
    await db.commit()
    return RedirectResponse("/admin/personalities", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/admin/personalities/{personality_id}/delete")
async def admin_personality_delete(
    personality_id: int, db: AsyncSession = Depends(get_session)
) -> RedirectResponse:
    personality = await db.get(Personality, personality_id)
    if personality:
        await db.delete(personality)
        await db.commit()
    return RedirectResponse("/admin/personalities", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/sessions", response_class=HTMLResponse)
async def admin_sessions(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await db.execute(
        select(Session)
        .options(
            selectinload(Session.messages),
            selectinload(Session.user),
        )
        .order_by(Session.created_at.desc())
    )
    sessions = result.scalars().unique().all()
    return templates.TemplateResponse(
        "sessions.html",
        {
            "request": request,
            "title": "Сессии",
            "sessions": sessions,
        },
    )


@app.post("/admin/sessions/{session_id}/stop")
async def admin_stop_session(session_id: int, db: AsyncSession = Depends(get_session)) -> RedirectResponse:
    orchestrator = DialogueOrchestrator(db)
    await orchestrator.stop_session(session_id)
    await db.commit()
    return RedirectResponse("/admin/sessions", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    result = await db.execute(select(Setting).order_by(Setting.key))
    settings = result.scalars().all()
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "title": "Настройки",
            "settings": settings,
        },
    )


@app.post("/admin/settings/new")
async def admin_setting_create(request: Request, db: AsyncSession = Depends(get_session)) -> HTMLResponse:
    form = await request.form()
    key = form.get("key", "").strip()
    value = form.get("value", "").strip()
    errors: list[str] = []
    if not key:
        errors.append("Ключ обязателен для заполнения")

    if errors:
        result = await db.execute(select(Setting).order_by(Setting.key))
        settings = result.scalars().all()
        return templates.TemplateResponse(
            "settings.html",
            {
                "request": request,
                "title": "Настройки",
                "settings": settings,
                "errors": errors,
                "form": {"key": key, "value": value},
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    existing = await db.get(Setting, key)
    if existing:
        existing.value = value
    else:
        db.add(Setting(key=key, value=value))
    await db.commit()
    return RedirectResponse("/admin/settings", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/admin/settings/{key}/update")
async def admin_setting_update(
    key: str, request: Request, db: AsyncSession = Depends(get_session)
) -> RedirectResponse:
    setting = await db.get(Setting, key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    form = await request.form()
    setting.value = form.get("value", "").strip()
    await db.commit()
    return RedirectResponse("/admin/settings", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/admin/settings/{key}/delete")
async def admin_setting_delete(key: str, db: AsyncSession = Depends(get_session)) -> RedirectResponse:
    setting = await db.get(Setting, key)
    if setting:
        await db.delete(setting)
        await db.commit()
    return RedirectResponse("/admin/settings", status_code=status.HTTP_303_SEE_OTHER)


@app.on_event("startup")
async def startup_event() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        orchestrator = DialogueOrchestrator(session, settings=settings)
        await orchestrator.ensure_user(telegram_id=0, username="system")
