from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator, Dict

import httpx

API_BASE = os.getenv("API_BASE_URL", "http://api:8000")


async def api_post(path: str, json: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{API_BASE}{path}", json=json)
        response.raise_for_status()
        return response.json()


async def api_get(path: str) -> Any:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(f"{API_BASE}{path}")
        response.raise_for_status()
        return response.json()


async def api_post_stream(path: str, json: dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST", f"{API_BASE}{path}", json=json, params={"stream": "true"}
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                yield json.loads(line)
