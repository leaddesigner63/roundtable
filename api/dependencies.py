from __future__ import annotations

from typing import AsyncIterator

from core.db import session_scope


async def get_session() -> AsyncIterator:
    async with session_scope() as session:
        yield session
