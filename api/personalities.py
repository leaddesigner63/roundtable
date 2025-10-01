from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit_log
from core.models import Personality
from core.schemas import PersonalityCreate, PersonalityRead

from .dependencies import get_session

router = APIRouter(prefix="/personalities", tags=["personalities"])


@router.get("/", response_model=list[PersonalityRead])
async def list_personalities(session: AsyncSession = Depends(get_session)) -> list[Personality]:
    result = await session.execute(select(Personality).order_by(Personality.title))
    return list(result.scalars())


@router.post("/", response_model=PersonalityRead, status_code=status.HTTP_201_CREATED)
async def create_personality(payload: PersonalityCreate, session: AsyncSession = Depends(get_session)) -> Personality:
    personality = Personality(**payload.model_dump())
    session.add(personality)
    await session.flush()
    await write_audit_log(session, actor="admin", action="create_personality", meta={"personality_id": personality.id})
    return personality


@router.get("/{personality_id}", response_model=PersonalityRead)
async def get_personality(personality_id: int, session: AsyncSession = Depends(get_session)) -> Personality:
    personality = await session.get(Personality, personality_id)
    if not personality:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personality not found")
    return personality


@router.delete("/{personality_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_personality(personality_id: int, session: AsyncSession = Depends(get_session)) -> None:
    personality = await session.get(Personality, personality_id)
    if not personality:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personality not found")
    await session.delete(personality)
    await write_audit_log(session, actor="admin", action="delete_personality", meta={"personality_id": personality_id})
