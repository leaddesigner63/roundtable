from __future__ import annotations

from contextlib import asynccontextmanager
from itertools import cycle

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.base import ProviderRegistry
from adapters.local_echo import EchoAdapter
from core import schemas
from core.config import settings
from core.database import SessionLocal, engine
from core.models import AuthorType, Personality, Provider, Session, SessionStatus
from core.security import cipher
from core.services import (
    add_message,
    create_session,
    get_or_create_user,
    log_action,
    update_session_status,
    upsert_setting,
)
from orchestrator.engine import OrchestratorConfig, RoundTableOrchestrator
from core.routes import audit as audit_routes
from core.routes import personalities as personalities_routes
from core.routes import providers as providers_routes
from core.routes import settings as settings_routes
from worker.tasks import enqueue_session_run

templates = Jinja2Templates(directory="admin/templates")

registry = ProviderRegistry()
registry.register("echo", EchoAdapter())

config = OrchestratorConfig(
    max_rounds=settings.max_rounds,
    context_token_limit=settings.context_token_limit,
    turn_timeout=settings.turn_timeout_sec,
)


def get_db():
    async def _get_db():
        async with SessionLocal() as session:
            yield session

    return _get_db


def get_orchestrator() -> RoundTableOrchestrator:
    return RoundTableOrchestrator(registry=registry, config=config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(providers_routes.router, prefix="/api")
app.include_router(personalities_routes.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(audit_routes.router, prefix="/api")


async def _load_providers(db: AsyncSession) -> list[Provider]:
    result = await db.execute(
        select(Provider).where(Provider.enabled.is_(True)).order_by(Provider.order_index)
    )
    providers = list(result.scalars())
    for provider in providers:
        setattr(provider, "api_key_plain", cipher.decrypt(provider.api_key))
    return providers


@app.post("/api/sessions", response_model=schemas.SessionRead)
async def api_create_session(
    payload: schemas.SessionCreate,
    db: AsyncSession = Depends(get_db()),
):
    providers = await _load_providers(db)
    if not providers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No providers configured")

    personalities = (
        await db.execute(select(Personality).order_by(Personality.id))
    ).scalars().all()
    if not personalities:
        raise HTTPException(status_code=400, detail="No personalities configured")

    participant_pairs = []
    personality_cycle = cycle(personalities)
    for provider in providers:
        personality = next(personality_cycle)
        participant_pairs.append((provider, personality))

    user = await get_or_create_user(db, telegram_id=0, username="api")
    session_obj = await create_session(
        db,
        user=user,
        topic=payload.topic,
        participants=participant_pairs,
        max_rounds=payload.max_rounds or settings.max_rounds,
    )
    await add_message(
        db,
        session_obj=session_obj,
        author_type=AuthorType.SYSTEM,
        author_name="system",
        content=f"Session created for topic '{payload.topic}'",
    )
    await db.commit()
    return schemas.SessionRead.model_validate(session_obj)


@app.post("/api/sessions/{session_id}/start", response_model=schemas.SessionStartResponse)
async def api_start_session(session_id: int, db: AsyncSession = Depends(get_db())):
    session_obj = await db.get(Session, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    if session_obj.status not in {SessionStatus.CREATED, SessionStatus.STOPPED}:
        raise HTTPException(status_code=400, detail="Session already running")
    await update_session_status(db, session_obj, SessionStatus.RUNNING)
    await db.commit()
    enqueue_session_run(session_id)
    return schemas.SessionStartResponse(session_id=session_obj.id, status=session_obj.status)


@app.post("/api/sessions/{session_id}/stop", response_model=schemas.SessionRead)
async def api_stop_session(session_id: int, db: AsyncSession = Depends(get_db())):
    session_obj = await db.get(Session, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    await update_session_status(db, session_obj, SessionStatus.STOPPED)
    await db.commit()
    return schemas.SessionRead.model_validate(session_obj)


@app.get("/api/sessions/{session_id}", response_model=schemas.SessionDetail)
async def api_get_session(session_id: int, db: AsyncSession = Depends(get_db())):
    session_obj = await db.get(Session, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    return schemas.SessionDetail(
        **schemas.SessionRead.model_validate(session_obj).model_dump(),
        messages=[schemas.MessageRead.model_validate(m) for m in session_obj.messages],
    )


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: AsyncSession = Depends(get_db())):
    providers = (await db.execute(select(Provider))).scalars().all()
    personalities = (await db.execute(select(Personality))).scalars().all()
    sessions = (await db.execute(select(Session))).scalars().all()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "providers": providers,
            "personalities": personalities,
            "sessions": sessions,
            "payment_url": settings.payment_url,
        },
    )


@app.post("/admin/settings/{key}")
async def admin_update_setting(key: str, request: Request, db: AsyncSession = Depends(get_db())):
    form = await request.form()
    await upsert_setting(db, key, form.get("value", ""))
    await log_action(db, actor="admin", action="update_setting", meta=key)
    await db.commit()
    return HTMLResponse(status_code=204)


@app.on_event("startup")
async def startup_event() -> None:
    registry.register("chatgpt", EchoAdapter(name="ChatGPT"))
    registry.register("deepseek", EchoAdapter(name="DeepSeek"))
