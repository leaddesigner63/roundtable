import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core import database
from core.main import app
import core.main as core_main
from core.models import Base, Personality, Provider
from core.security import cipher


@pytest.fixture(autouse=True, scope="module")
async def setup_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    database.engine = engine
    database.SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    core_main.engine = engine
    core_main.SessionLocal = database.SessionLocal
    yield
    await engine.dispose()


@pytest.mark.asyncio
async def test_admin_dashboard_access():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/admin")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_and_start_session():
    async with database.SessionLocal() as session:
        provider = Provider(
            name="Echo",
            type="echo",
            api_key=cipher.encrypt("k"),
            model_id="echo",
            parameters="{}",
            enabled=True,
        )
        personality = Personality(title="Test", instructions="Test", style="Neutral")
        session.add_all([provider, personality])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/sessions", json={"topic": "API Test"})
        assert response.status_code == 200
        session_id = response.json()["id"]

        start_resp = await client.post(f"/api/sessions/{session_id}/start")
        assert start_resp.status_code == 200
