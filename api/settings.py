from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit_log
from core.models import Setting
from core.schemas import SettingRead, SettingUpdate

from .dependencies import get_session

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/", response_model=list[SettingRead])
async def list_settings(session: AsyncSession = Depends(get_session)) -> list[Setting]:
    result = await session.execute(select(Setting).order_by(Setting.key))
    return list(result.scalars())


@router.put("/{key}", response_model=SettingRead)
async def update_setting(key: str, payload: SettingUpdate, session: AsyncSession = Depends(get_session)) -> Setting:
    setting = await session.get(Setting, key)
    if not setting:
        setting = Setting(key=key, value=payload.value)
        session.add(setting)
    else:
        setting.value = payload.value
    await session.flush()
    await write_audit_log(session, actor="admin", action="update_setting", meta={"key": key})
    return setting
