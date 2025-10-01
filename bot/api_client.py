from __future__ import annotations

import os
from typing import Any

import httpx

API_BASE = os.getenv("API_BASE_URL", "http://api:8000")


async def api_post(path: str, json: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{API_BASE}{path}", json=json)
        response.raise_for_status()
        return response.json()


async def api_get(path: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(f"{API_BASE}{path}")
        response.raise_for_status()
        return response.json()
