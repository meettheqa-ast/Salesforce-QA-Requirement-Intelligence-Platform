"""Connections: sealed credential round-trip, audited decrypt, and RLS.

DB-gated. Proves the secret is never stored in clear, get_credentials_for_use
returns the real secret in-process, and a tenant cannot read another tenant's
connection rows.
"""

from __future__ import annotations

import uuid

import pytest
from app.context import set_request_context
from app.db import system_session, tenant_session
from app.modules.connections._internal.models import Connection
from app.modules.connections.api import (
    ConnectionCreate,
    create_connection,
    get_credentials_for_use,
)
from sqlalchemy import select, text

pytestmark = pytest.mark.asyncio


async def _db_available() -> bool:
    try:
        async with system_session() as session:
            await session.execute(text("select 1"))
        return True
    except Exception:
        return False


def _seed_tenant(tenant_id: str) -> None:
    set_request_context(request_id="t", tenant_id=tenant_id, user_id=None)


async def test_secret_is_sealed_and_recoverable() -> None:
    if not await _db_available():
        pytest.skip("database not available")

    tenant_id = str(uuid.uuid4())
    _seed_tenant(tenant_id)

    secret = "jira-api-token-abc123"
    conn = await create_connection(
        ConnectionCreate(
            name="Acme Jira",
            base_url="https://acme.atlassian.net",
            principal="qa@acme.com",
            secret=secret,
        )
    )

    # The persisted row must NOT contain the plaintext secret anywhere.
    async with tenant_session(tenant_id) as session:
        row = await session.get(Connection, conn.id)
        assert row is not None
        assert secret not in row.sealed_secret
        assert row.principal == "qa@acme.com"

    # In-process retrieval returns the real secret.
    creds = await get_credentials_for_use(conn.id, purpose="test")
    assert creds.secret == secret
    assert creds.principal == "qa@acme.com"


async def test_rls_blocks_cross_tenant_connection_reads() -> None:
    if not await _db_available():
        pytest.skip("database not available")

    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    _seed_tenant(tenant_a)
    conn_a = await create_connection(
        ConnectionCreate(
            name="A", base_url="https://a.example", secret="sa", principal="a"
        )
    )

    _seed_tenant(tenant_b)
    await create_connection(
        ConnectionCreate(
            name="B", base_url="https://b.example", secret="sb", principal="b"
        )
    )

    # Tenant B's scoped session must not see tenant A's connection.
    async with tenant_session(tenant_b) as session:
        ids = {
            c.id for c in (await session.execute(select(Connection))).scalars().all()
        }
    assert conn_a.id not in ids, "RLS LEAK: tenant B saw tenant A's connection"
