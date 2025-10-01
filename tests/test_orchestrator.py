import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from adapters.base import ProviderRegistry
from adapters.local_echo import EchoAdapter
from core.models import Base, Personality, Provider, Session, SessionParticipant, SessionStatus, User
from orchestrator.engine import OrchestratorConfig, RoundTableOrchestrator


@pytest.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncSession:
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session


@pytest.mark.asyncio
async def test_orchestrator_runs_rounds(db_session):
    user = User(telegram_id=1, username="tester")
    provider = Provider(name="Echo", type="echo", api_key="k", model_id="echo", parameters=None, enabled=True)
    personality = Personality(title="Test", instructions="", style="")
    session_obj = Session(user=user, topic="Test topic", max_rounds=2)
    participant = SessionParticipant(session=session_obj, provider=provider, personality=personality)
    db_session.add_all([user, provider, personality, session_obj, participant])
    await db_session.commit()

    registry = ProviderRegistry()
    registry.register("echo", EchoAdapter())
    orchestrator = RoundTableOrchestrator(
        registry=registry,
        config=OrchestratorConfig(max_rounds=2, context_token_limit=2000, turn_timeout=10),
    )

    await orchestrator.run(db_session, session_obj)
    assert session_obj.status in {SessionStatus.FINISHED, SessionStatus.STOPPED}
    assert len(session_obj.messages) > 0
