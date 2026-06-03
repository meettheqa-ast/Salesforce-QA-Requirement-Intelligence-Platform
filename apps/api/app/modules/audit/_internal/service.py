"""Audit emission and read logic."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.context import get_request_context
from app.db import system_session, tenant_session
from app.logging import get_logger

from .models import AuditEvent

log = get_logger(__name__)


async def emit(
    action: str,
    *,
    resource_type: str | None = None,
    resource_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Record an audit event, attributed to the current request context.

    Uses a system session because audit rows for not-yet-authenticated flows
    (e.g. onboarding) carry a null tenant_id and must still persist.
    """
    ctx = get_request_context()
    event = AuditEvent(
        tenant_id=uuid.UUID(ctx.tenant_id) if ctx.tenant_id else None,
        user_id=uuid.UUID(ctx.user_id) if ctx.user_id else None,
        request_id=ctx.request_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload or {},
    )
    async with system_session() as session:
        session.add(event)
    log.info(
        "audit.emit",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
    )


async def list_events(*, limit: int = 100) -> list[AuditEvent]:
    """List audit events for the current tenant (RLS-scoped)."""
    async with tenant_session() as session:
        result = await session.execute(
            select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
