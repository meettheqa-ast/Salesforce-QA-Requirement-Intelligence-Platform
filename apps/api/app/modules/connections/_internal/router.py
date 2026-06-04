"""HTTP routes for the connections module."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.api import Principal, require_role

from . import service
from .schemas import ConnectionCreate, ConnectionOut, HealthStatus

router = APIRouter(prefix="/connections", tags=["connections"])

_MANAGE = ("tenant_admin", "qa_lead")
_VIEW = ("tenant_admin", "qa_lead", "qa_engineer")


@router.post("", response_model=ConnectionOut, status_code=201)
async def create_connection(
    data: ConnectionCreate,
    _p: Principal = Depends(require_role(*_MANAGE)),
) -> ConnectionOut:
    return await service.create_connection(data)


@router.get("", response_model=list[ConnectionOut])
async def list_connections(
    _p: Principal = Depends(require_role(*_VIEW)),
) -> list[ConnectionOut]:
    return await service.list_connections()


@router.get("/{connection_id}", response_model=ConnectionOut)
async def get_connection(
    connection_id: uuid.UUID,
    _p: Principal = Depends(require_role(*_VIEW)),
) -> ConnectionOut:
    conn = await service.get_connection(connection_id)
    if conn is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


@router.post("/{connection_id}/health", response_model=HealthStatus)
async def check_health(
    connection_id: uuid.UUID,
    _p: Principal = Depends(require_role(*_VIEW)),
) -> HealthStatus:
    try:
        return await service.check_health(connection_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
