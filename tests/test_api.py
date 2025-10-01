from __future__ import annotations

from fastapi.testclient import TestClient


def test_full_session_flow(client: TestClient) -> None:
    provider_payload = {
        "name": "Mock",
        "type": "mock",
        "api_key": "secret",
        "model_id": "mock-model",
        "parameters": {},
        "enabled": True,
        "order_index": 0,
    }
    response = client.post("/api/providers/", json=provider_payload)
    assert response.status_code == 201

    personality_payload = {
        "title": "Strategist",
        "instructions": "Provide strategic insights",
        "style": "formal",
    }
    response = client.post("/api/personalities/", json=personality_payload)
    assert response.status_code == 201

    session_payload = {
        "user_id": 1001,
        "username": "alice",
        "topic": "Responsible AI",
        "max_rounds": 2,
    }
    response = client.post("/api/sessions/", json=session_payload)
    assert response.status_code == 201
    session_data = response.json()
    session_id = session_data["id"]
    assert session_data["status"] == "created"

    response = client.post(f"/api/sessions/{session_id}/start")
    assert response.status_code == 200
    assert response.json()["status"] in {"running", "finished"}

    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["messages"], "messages should not be empty"

    admin_response = client.get("/admin/sessions")
    assert admin_response.status_code == 200
    assert "Sessions" in admin_response.text
