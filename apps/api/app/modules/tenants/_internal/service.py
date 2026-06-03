"""Tenant/User/Membership business logic.

Tenant and user creation are onboarding operations that run before a tenant
context exists, so they use a system session. Audit events are emitted for
every mutation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select

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


@dataclass(frozen=True, slots=True)
class ResolvedIdentity:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str


async def resolve_identity(
    *, sso_subject: str, email: str
) -> ResolvedIdentity | None:
    """Resolve a user + their membership from an IdP subject or email.

    Used as the fallback when an OIDC token does not carry tenant/role custom
    claims. MVP assumes one active membership per user; if a user belongs to
    several tenants, the most recently created membership wins (deterministic,
    documented; multi-tenant user selection is a future concern).
    """
    async with system_session() as session:
        user = (
            await session.execute(
                select(User).where(
                    or_(User.sso_subject == sso_subject, User.email == email)
                )
            )
        ).scalar_one_or_none()
        if user is None:
            return None
        membership = (
            await session.execute(
                select(Membership)
                .where(Membership.user_id == user.id)
                .order_by(Membership.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if membership is None:
            return None
        return ResolvedIdentity(
            user_id=user.id,
            tenant_id=membership.tenant_id,
            role=membership.role,
        )


async def list_members(tenant_id: uuid.UUID) -> list[MembershipOut]:
    async with system_session() as session:
        result = await session.execute(
            select(Membership).where(Membership.tenant_id == tenant_id)
        )
        return [MembershipOut.model_validate(m) for m in result.scalars().all()]
