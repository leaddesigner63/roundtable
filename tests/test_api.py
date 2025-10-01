from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from admin.main import app
from core import db as core_db
import orchestrator.service as service_module


@pytest.fixture(autouse=True)
async def override_dependencies(db_session):
    async def _override_get_session():
        async with core_db.AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[core_db.get_session] = _override_get_session  # type: ignore[attr-defined]
    yield
    app.dependency_overrides.clear()


class ApiStubAdapter:
    def __init__(self) -> None:
        self.counter = 0

    async def complete(self, prompt, context):
        self.counter += 1
        return f"Ответ API {self.counter}", {"prompt_tokens": 5, "completion_tokens": 5, "cost": 0.002}


@pytest.mark.asyncio
async def test_full_session_flow(monkeypatch):
    stub = ApiStubAdapter()

    def adapter_factory(provider_type, api_key, model, **params):
        return stub

    monkeypatch.setattr(service_module, "create_adapter", adapter_factory)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        provider_payload = {
            "name": "OpenAI",
            "type": "openai",
            "api_key": "key",
            "model_id": "gpt",
            "parameters": {},
            "enabled": True,
            "order_index": 0,
        }
        response = await client.post("/api/providers", json=provider_payload)
        assert response.status_code == 201

        personality_payload = {"title": "Expert", "instructions": "Будь экспертом", "style": "Формально"}
        response = await client.post("/api/personalities", json=personality_payload)
        assert response.status_code == 201

        response = await client.post("/api/users", json={"telegram_id": 1, "username": "tester"})
        assert response.status_code == 201

        session_payload = {"user_id": 1, "topic": "ИИ в образовании", "max_rounds": 1}
        response = await client.post("/api/sessions", json=session_payload)
        assert response.status_code == 201
        session_id = response.json()["id"]

        response = await client.post(f"/api/sessions/{session_id}/start")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in {"running", "finished", "stopped"}

        response = await client.get(f"/api/sessions/{session_id}")
        assert response.status_code == 200
        assert response.json()["id"] == session_id


@pytest.mark.asyncio
async def test_streaming_session_flow(monkeypatch):
    stub = ApiStubAdapter()

    def adapter_factory(provider_type, api_key, model, **params):
        return stub

    monkeypatch.setattr(service_module, "create_adapter", adapter_factory)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        provider_payload = {
            "name": "OpenAI",
            "type": "openai",
            "api_key": "key",
            "model_id": "gpt",
            "parameters": {},
            "enabled": True,
            "order_index": 0,
        }
        response = await client.post("/api/providers", json=provider_payload)
        assert response.status_code == 201

        personality_payload = {
            "title": "Expert",
            "instructions": "Будь экспертом",
            "style": "Формально",
        }
        response = await client.post("/api/personalities", json=personality_payload)
        assert response.status_code == 201

        response = await client.post("/api/users", json={"telegram_id": 1, "username": "tester"})
        assert response.status_code == 201

        session_payload = {"user_id": 1, "topic": "ИИ в образовании", "max_rounds": 2}
        response = await client.post("/api/sessions", json=session_payload)
        assert response.status_code == 201
        session_id = response.json()["id"]

        events: list[dict] = []
        async with client.stream(
            "POST", f"/api/sessions/{session_id}/start", params={"stream": "true"}
        ) as response:
            assert response.status_code == 200
            async for line in response.aiter_lines():
                if not line:
                    continue
                events.append(json.loads(line))

        message_events = [event for event in events if event.get("type") == "message"]
        assert len(message_events) == 2
        assert events[-1]["type"] == "session"
        assert events[-1]["status"] == "finished"
        assert events[-1]["current_round"] == 2


@pytest.mark.asyncio
async def test_stop_session_during_stream(monkeypatch):
    class SlowStubAdapter(ApiStubAdapter):
        async def complete(self, prompt, context):
            self.counter += 1
            await asyncio.sleep(0.05)
            return f"Ответ API {self.counter}", {"prompt_tokens": 5, "completion_tokens": 5, "cost": 0.002}

    stub = SlowStubAdapter()

    def adapter_factory(provider_type, api_key, model, **params):
        return stub

    monkeypatch.setattr(service_module, "create_adapter", adapter_factory)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        provider_payload = {
            "name": "OpenAI",
            "type": "openai",
            "api_key": "key",
            "model_id": "gpt",
            "parameters": {},
            "enabled": True,
            "order_index": 0,
        }
        response = await client.post("/api/providers", json=provider_payload)
        assert response.status_code == 201
        personality_payload = {
            "title": "Expert",
            "instructions": "Будь экспертом",
            "style": "Формально",
        }
        response = await client.post("/api/personalities", json=personality_payload)
        assert response.status_code == 201
        response = await client.post("/api/users", json={"telegram_id": 2, "username": "tester"})
        assert response.status_code == 201
        session_payload = {"user_id": 2, "topic": "ИИ и этика", "max_rounds": 3}
        response = await client.post("/api/sessions", json=session_payload)
        session_id = response.json()["id"]

        events: list[dict] = []

        async def stop_soon():
            await asyncio.sleep(0.01)
            return await client.post(f"/api/sessions/{session_id}/stop")

        stop_task = asyncio.create_task(stop_soon())
        async with client.stream(
            "POST", f"/api/sessions/{session_id}/start", params={"stream": "true"}
        ) as response:
            async for line in response.aiter_lines():
                if not line:
                    continue
                events.append(json.loads(line))

        stop_response = await stop_task
        assert stop_response.status_code == 200
        assert stop_response.json()["status"] == "stopped"
        assert events[-1]["type"] == "session"
        assert events[-1]["status"] == "stopped"
        message_events = [event for event in events if event.get("type") == "message"]
        assert len(message_events) <= 1
