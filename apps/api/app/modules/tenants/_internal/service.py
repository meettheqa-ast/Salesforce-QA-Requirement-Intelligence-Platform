"""Tenant/User/Membership business logic.

Tenant and user creation are onboarding operations that run before a tenant
context exists, so they use a system session. Audit events are emitted for
every mutation.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.db import system_session
from app.modules.audit.api import emit

from .models import Membership, Tenant, User
from .schemas import (
    MembershipCreate,
    MembershipOut,
    TenantCreate,
    TenantOut,
    UserCreate,
    UserOut,
)


async def create_tenant(data: TenantCreate) -> TenantOut:
    async with system_session() as session:
        tenant = Tenant(name=data.name, tier=data.tier.value, region=data.region)
        session.add(tenant)
        await session.flush()
        out = TenantOut.model_validate(tenant)
    await emit("tenant.created", resource_type="tenant", resource_id=str(out.id))
    return out


async def get_tenant(tenant_id: uuid.UUID) -> TenantOut | None:
    async with system_session() as session:
        tenant = await session.get(Tenant, tenant_id)
        return TenantOut.model_validate(tenant) if tenant else None


async def list_tenants() -> list[TenantOut]:
    async with system_session() as session:
        result = await session.execute(select(Tenant).order_by(Tenant.created_at))
        return [TenantOut.model_validate(t) for t in result.scalars().all()]


async def create_user(data: UserCreate) -> UserOut:
    async with system_session() as session:
        user = User(email=data.email, sso_subject=data.sso_subject)
        session.add(user)
        await session.flush()
        out = UserOut.model_validate(user)
    await emit("user.created", resource_type="user", resource_id=str(out.id))
    return out


async def add_member(data: MembershipCreate) -> MembershipOut:
    async with system_session() as session:
        membership = Membership(
            user_id=data.user_id, tenant_id=data.tenant_id, role=data.role.value
        )
        session.add(membership)
        await session.flush()
        out = MembershipOut.model_validate(membership)
    await emit(
        "membership.created",
        resource_type="membership",
        resource_id=str(out.id),
        payload={"tenant_id": str(data.tenant_id), "role": data.role.value},
    )
    return out


async def list_members(tenant_id: uuid.UUID) -> list[MembershipOut]:
    async with system_session() as session:
        result = await session.execute(
            select(Membership).where(Membership.tenant_id == tenant_id)
        )
        return [MembershipOut.model_validate(m) for m in result.scalars().all()]
