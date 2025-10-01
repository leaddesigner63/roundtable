from __future__ import annotations

from fastapi import FastAPI

from admin import router as admin_router
from core.config import settings
from core.db import async_engine
from core.models import Base

from . import audit, personalities, providers, sessions, settings as settings_router

app = FastAPI(title="Roundtable AI")


@app.on_event("startup")
async def startup() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(providers.router, prefix="/api")
app.include_router(personalities.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(admin_router.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
