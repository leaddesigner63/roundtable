from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import schemas
from core.database import SessionLocal
from core.models import Setting

router = APIRouter(prefix="/settings", tags=["settings"])


def get_db():
    async def _get_db():
        async with SessionLocal() as session:
            yield session

    return _get_db


@router.get("", response_model=list[schemas.SettingRead])
async def list_settings(db: AsyncSession = Depends(get_db())):
    result = await db.execute(select(Setting))
    return [schemas.SettingRead.model_validate(item) for item in result.scalars().all()]


@router.put("/{key}", response_model=schemas.SettingRead)
async def update_setting(key: str, payload: schemas.SettingUpdate, db: AsyncSession = Depends(get_db())):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = Setting(key=key, value=payload.value)
        db.add(setting)
    else:
        setting.value = payload.value
    await db.commit()
    return schemas.SettingRead.model_validate(setting)


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(key: str, db: AsyncSession = Depends(get_db())):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    await db.delete(setting)
    await db.commit()
