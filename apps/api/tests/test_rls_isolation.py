"""Cross-tenant RLS isolation probe. Requires a live, migrated database.

This is the single most security-critical test in the foundation. It proves
that a session scoped to tenant A cannot read tenant B's rows, and that the
system session can. Skipped automatically if the database is unreachable.
"""

from __future__ import annotations

import uuid

import pytest
from app.context import set_request_context
from app.db import system_session, tenant_session
from app.modules.metering._internal.models import UsageMeter
from sqlalchemy import select, text

pytestmark = pytest.mark.asyncio


async def _db_available() -> bool:
    try:
        async with system_session() as session:
            await session.execute(text("select 1"))
        return True
    except Exception:
        return False


async def test_rls_blocks_cross_tenant_reads() -> None:
    if not await _db_available():
        pytest.skip("database not available")

    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    # Seed one usage row for each tenant via the system (bypass) session.
    async with system_session() as session:
        session.add(
            UsageMeter(
                tenant_id=tenant_a,
                period_month="2026-06",
                model="stub",
                cost_cents=1,
            )
        )
        session.add(
            UsageMeter(
                tenant_id=tenant_b,
                period_month="2026-06",
                model="stub",
                cost_cents=1,
            )
        )

    # A tenant-scoped session for tenant A must see ONLY tenant A's row.
    set_request_context(
        request_id="t", tenant_id=str(tenant_a), user_id=None
    )
    async with tenant_session(str(tenant_a)) as session:
        rows = (
            (await session.execute(select(UsageMeter))).scalars().all()
        )
    seen_tenants = {r.tenant_id for r in rows}
    assert tenant_a in seen_tenants
    assert tenant_b not in seen_tenants, "RLS LEAK: tenant A saw tenant B rows"


async def test_system_session_sees_all_tenants() -> None:
    if not await _db_available():
        pytest.skip("database not available")

    # Seed two tenants' rows in this test so it does not depend on test order.
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    async with system_session() as session:
        session.add(
            UsageMeter(
                tenant_id=tenant_a, period_month="2026-07", model="stub", cost_cents=1
            )
        )
        session.add(
            UsageMeter(
                tenant_id=tenant_b, period_month="2026-07", model="stub", cost_cents=1
            )
        )

    async with system_session() as session:
        rows = (await session.execute(select(UsageMeter))).scalars().all()
    seen = {r.tenant_id for r in rows}
    assert tenant_a in seen and tenant_b in seen, (
        "system session should bypass RLS and see all tenants' rows"
    )
