"""HTTP routes for the tenants module.

Tenant and user creation are onboarding/admin operations. In Sprint 0 they are
open for local development; Sprint 1 gates them behind admin authorization.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from . import service
from .schemas import (
    MembershipCreate,
    MembershipOut,
    TenantCreate,
    TenantOut,
    UserCreate,
    UserOut,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantOut, status_code=201)
async def create_tenant(data: TenantCreate) -> TenantOut:
    return await service.create_tenant(data)


@router.get("", response_model=list[TenantOut])
async def list_tenants() -> list[TenantOut]:
    return await service.list_tenants()


@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant(tenant_id: uuid.UUID) -> TenantOut:
    tenant = await service.get_tenant(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.post("/{tenant_id}/members", response_model=MembershipOut, status_code=201)
async def add_member(tenant_id: uuid.UUID, data: MembershipCreate) -> MembershipOut:
    if data.tenant_id != tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id mismatch")
    return await service.add_member(data)


@router.get("/{tenant_id}/members", response_model=list[MembershipOut])
async def list_members(tenant_id: uuid.UUID) -> list[MembershipOut]:
    return await service.list_members(tenant_id)


# Users live under tenants router for Sprint 0 simplicity.
users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.post("", response_model=UserOut, status_code=201)
async def create_user(data: UserCreate) -> UserOut:
    return await service.create_user(data)


router.include_router(users_router)
