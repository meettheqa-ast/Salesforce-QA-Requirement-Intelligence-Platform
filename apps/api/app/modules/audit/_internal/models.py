"""Audit event ORM model. Append-only; never updated or deleted in app code."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models_common import TimestampMixin, UUIDPrimaryKeyMixin


class AuditEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_events"

    # Nullable because some events (e.g. system onboarding) are not tenant-scoped.
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    request_id: Mapped[str | None] = mapped_column(nullable=True)
    action: Mapped[str] = mapped_column(nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(nullable=True)
    resource_id: Mapped[str | None] = mapped_column(nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
