from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import schemas
from core.database import SessionLocal
from core.models import Personality

router = APIRouter(prefix="/personalities", tags=["personalities"])


def get_db():
    async def _get_db():
        async with SessionLocal() as session:
            yield session

    return _get_db


@router.get("", response_model=list[schemas.PersonalityRead])
async def list_personalities(db: AsyncSession = Depends(get_db())):
    result = await db.execute(select(Personality).order_by(Personality.id))
    return [schemas.PersonalityRead.model_validate(p) for p in result.scalars().all()]


@router.post("", response_model=schemas.PersonalityRead, status_code=status.HTTP_201_CREATED)
async def create_personality(
    payload: schemas.PersonalityCreate,
    db: AsyncSession = Depends(get_db()),
):
    personality = Personality(**payload.model_dump())
    db.add(personality)
    await db.commit()
    await db.refresh(personality)
    return schemas.PersonalityRead.model_validate(personality)


@router.patch("/{personality_id}", response_model=schemas.PersonalityRead)
async def update_personality(
    personality_id: int,
    payload: schemas.PersonalityUpdate,
    db: AsyncSession = Depends(get_db()),
):
    personality = await db.get(Personality, personality_id)
    if not personality:
        raise HTTPException(status_code=404, detail="Personality not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(personality, field, value)
    await db.commit()
    await db.refresh(personality)
    return schemas.PersonalityRead.model_validate(personality)


@router.delete("/{personality_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_personality(personality_id: int, db: AsyncSession = Depends(get_db())):
    personality = await db.get(Personality, personality_id)
    if not personality:
        raise HTTPException(status_code=404, detail="Personality not found")
    await db.delete(personality)
    await db.commit()
