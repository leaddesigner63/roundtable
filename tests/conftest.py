from __future__ import annotations

import asyncio
import os
from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Ensure deterministic environment for tests
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRETS_KEY", "Xh4O8zJS1-WxxFjNV8iP-9e1X2-b4PqQjLTrBqkHqBw=")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("PAYMENT_URL", "https://example.com/pay")
os.environ.setdefault("ENVIRONMENT", "test")

from api.main import app
from core import config as config_module
from core import db as db_module
from core import security as security_module
from core.models import Base

config_module.get_settings.cache_clear()
settings = config_module.get_settings()
security_module.cipher = security_module.SecretsCipher(settings.secrets_key)


@pytest.fixture(scope="session")
def event_loop() -> AsyncIterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def configure_database() -> AsyncIterator[None]:
    test_engine = create_async_engine(
        settings.database_url,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    db_module.async_engine = test_engine
    db_module.AsyncSessionMaker = async_session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await test_engine.dispose()


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with db_module.AsyncSessionMaker() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture
def client(configure_database) -> AsyncIterator[TestClient]:  # type: ignore[override]
    with TestClient(app) as client:
        yield client
