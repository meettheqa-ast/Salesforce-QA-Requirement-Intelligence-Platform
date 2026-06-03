"""Public API of the tenants module: service functions, DTOs, and the router."""

from __future__ import annotations

from app.modules.tenants._internal.models import MemberRole, TenantStatus, TenantTier
from app.modules.tenants._internal.router import router
from app.modules.tenants._internal.schemas import (
    MembershipCreate,
    MembershipOut,
    TenantCreate,
    TenantOut,
    UserCreate,
    UserOut,
)
from app.modules.tenants._internal.service import (
    add_member,
    create_tenant,
    create_user,
    get_tenant,
    list_members,
    list_tenants,
)

__all__ = [
    "MemberRole",
    "MembershipCreate",
    "MembershipOut",
    "TenantCreate",
    "TenantOut",
    "TenantStatus",
    "TenantTier",
    "UserCreate",
    "UserOut",
    "add_member",
    "create_tenant",
    "create_user",
    "get_tenant",
    "list_members",
    "list_tenants",
    "router",
]
