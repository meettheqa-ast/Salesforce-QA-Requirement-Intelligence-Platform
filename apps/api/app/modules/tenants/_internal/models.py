"""Tenant, User, and Membership ORM models."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models_common import TimestampMixin, UUIDPrimaryKeyMixin


class TenantTier(StrEnum):
    POOLED = "pooled"
    SILO = "silo"


class TenantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class MemberRole(StrEnum):
    TENANT_ADMIN = "tenant_admin"
    QA_LEAD = "qa_lead"
    QA_ENGINEER = "qa_engineer"
    VIEWER = "viewer"


class Tenant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(nullable=False)
    tier: Mapped[str] = mapped_column(nullable=False, default=TenantTier.POOLED.value)
    region: Mapped[str] = mapped_column(nullable=False, default="us-east-1")
    status: Mapped[str] = mapped_column(
        nullable=False, default=TenantStatus.ACTIVE.value
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    kms_key_alias: Mapped[str | None] = mapped_column(nullable=True)


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    sso_subject: Mapped[str | None] = mapped_column(nullable=True, index=True)


class Membership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(
        nullable=False, default=MemberRole.QA_ENGINEER.value
    )
