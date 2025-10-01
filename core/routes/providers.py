from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import schemas
from core.database import SessionLocal
from core.models import Provider
from core.security import cipher

router = APIRouter(prefix="/providers", tags=["providers"])


def get_db():
    async def _get_db():
        async with SessionLocal() as session:
            yield session

    return _get_db


@router.get("", response_model=list[schemas.ProviderRead])
async def list_providers(db: AsyncSession = Depends(get_db())):
    result = await db.execute(select(Provider).order_by(Provider.order_index))
    providers = list(result.scalars())
    items = []
    for provider in providers:
        params = None
        if provider.parameters:
            try:
                params = json.loads(provider.parameters)
            except json.JSONDecodeError:
                params = None
        items.append(
            schemas.ProviderRead(
                id=provider.id,
                name=provider.name,
                type=provider.type,
                model_id=provider.model_id,
                parameters=params,
                enabled=provider.enabled,
                order_index=provider.order_index,
            )
        )
    return items


@router.post("", response_model=schemas.ProviderRead, status_code=status.HTTP_201_CREATED)
async def create_provider(payload: schemas.ProviderCreate, db: AsyncSession = Depends(get_db())):
    provider = Provider(
        name=payload.name,
        type=payload.type,
        api_key=cipher.encrypt(payload.api_key),
        model_id=payload.model_id,
        parameters=json.dumps(payload.parameters) if payload.parameters else None,
        enabled=payload.enabled,
        order_index=payload.order_index,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    params = payload.parameters if payload.parameters else None
    return schemas.ProviderRead(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        model_id=provider.model_id,
        parameters=params,
        enabled=provider.enabled,
        order_index=provider.order_index,
    )


@router.patch("/{provider_id}", response_model=schemas.ProviderRead)
async def update_provider(
    provider_id: int,
    payload: schemas.ProviderUpdate,
    db: AsyncSession = Depends(get_db()),
):
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "api_key" and value is not None:
            setattr(provider, field, cipher.encrypt(value))
        elif field == "parameters" and value is not None:
            setattr(provider, field, json.dumps(value))
        else:
            setattr(provider, field, value)
    await db.commit()
    await db.refresh(provider)
    params = None
    if provider.parameters:
        try:
            params = json.loads(provider.parameters)
        except json.JSONDecodeError:
            params = None
    return schemas.ProviderRead(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        model_id=provider.model_id,
        parameters=params,
        enabled=provider.enabled,
        order_index=provider.order_index,
    )


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db())):
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)
    await db.commit()
