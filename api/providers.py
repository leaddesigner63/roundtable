from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import write_audit_log
from core.models import Provider
from core.schemas import ProviderCreate, ProviderRead
from core.security import cipher

from .dependencies import get_session

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/", response_model=list[ProviderRead])
async def list_providers(session: AsyncSession = Depends(get_session)) -> list[Provider]:
    result = await session.execute(select(Provider).order_by(Provider.order_index))
    return list(result.scalars())


@router.post("/", response_model=ProviderRead, status_code=status.HTTP_201_CREATED)
async def create_provider(payload: ProviderCreate, session: AsyncSession = Depends(get_session)) -> Provider:
    provider = Provider(
        name=payload.name,
        type=payload.type,
        api_key_encrypted=cipher.encrypt(payload.api_key),
        model_id=payload.model_id,
        parameters=payload.parameters,
        enabled=payload.enabled,
        order_index=payload.order_index,
    )
    session.add(provider)
    await session.flush()
    await write_audit_log(session, actor="admin", action="create_provider", meta={"provider_id": provider.id})
    return provider


@router.get("/{provider_id}", response_model=ProviderRead)
async def get_provider(provider_id: int, session: AsyncSession = Depends(get_session)) -> Provider:
    provider = await session.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return provider


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(provider_id: int, session: AsyncSession = Depends(get_session)) -> None:
    provider = await session.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    await session.delete(provider)
    await write_audit_log(session, actor="admin", action="delete_provider", meta={"provider_id": provider_id})
