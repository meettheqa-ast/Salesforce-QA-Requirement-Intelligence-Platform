"""Connections business logic -- the ONLY module that opens sealed secrets.

Rules enforced here:
  - The plaintext credential is sealed on create and never persisted in clear.
  - get_credentials_for_use() is the single decrypt path and emits an audit
    event on every use (action, connection, caller) WITHOUT the secret value.
  - No function returns a secret to an HTTP response (see schemas).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import httpx
from sqlalchemy import select

from app.context import require_tenant_id
from app.crypto import open_secret, seal
from app.db import tenant_session
from app.logging import get_logger
from app.modules.audit.api import emit

from .models import Connection, ConnectionStatus
from .schemas import ConnectionCreate, ConnectionOut, HealthStatus

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class UsableCredentials:
    """In-process credential bundle. Must never be serialized to a response."""

    connection_id: uuid.UUID
    base_url: str
    auth_type: str
    principal: str
    secret: str


async def create_connection(data: ConnectionCreate) -> ConnectionOut:
    sealed = seal(data.secret)
    tenant_id = uuid.UUID(require_tenant_id())
    async with tenant_session() as session:
        conn = Connection(
            tenant_id=tenant_id,
            name=data.name,
            connection_type=data.connection_type.value,
            base_url=str(data.base_url).rstrip("/"),
            auth_type=data.auth_type.value,
            principal=data.principal,
            sealed_secret=sealed,
        )
        session.add(conn)
        await session.flush()
        out = ConnectionOut.model_validate(conn)
    await emit(
        "connection.created",
        resource_type="connection",
        resource_id=str(out.id),
        payload={"connection_type": out.connection_type, "base_url": out.base_url},
    )
    return out


async def get_connection(connection_id: uuid.UUID) -> ConnectionOut | None:
    async with tenant_session() as session:
        conn = await session.get(Connection, connection_id)
        return ConnectionOut.model_validate(conn) if conn else None


async def list_connections() -> list[ConnectionOut]:
    async with tenant_session() as session:
        result = await session.execute(select(Connection).order_by(Connection.created_at))
        return [ConnectionOut.model_validate(c) for c in result.scalars().all()]


async def get_credentials_for_use(
    connection_id: uuid.UUID, *, purpose: str
) -> UsableCredentials:
    """Decrypt and return credentials for in-process use only.

    Every call is audited with the stated purpose. The secret value is NEVER
    included in the audit payload or any log line.
    """
    async with tenant_session() as session:
        conn = await session.get(Connection, connection_id)
        if conn is None:
            raise LookupError(f"Connection {connection_id} not found")
        if conn.status != ConnectionStatus.ACTIVE.value:
            raise PermissionError(f"Connection {connection_id} is not active")
        secret = open_secret(conn.sealed_secret)
        creds = UsableCredentials(
            connection_id=conn.id,
            base_url=conn.base_url,
            auth_type=conn.auth_type,
            principal=conn.principal,
            secret=secret,
        )
    await emit(
        "connection.credentials_used",
        resource_type="connection",
        resource_id=str(connection_id),
        payload={"purpose": purpose},
    )
    return creds


async def check_health(connection_id: uuid.UUID) -> HealthStatus:
    """Lightweight connectivity probe to the connection's base URL.

    Auth-specific health (e.g. validating a Jira token) is the jira module's
    concern; this only confirms the endpoint is reachable.
    """
    conn = await get_connection(connection_id)
    if conn is None:
        raise LookupError(f"Connection {connection_id} not found")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(conn.base_url)
        healthy = resp.status_code < 500
        detail = f"HTTP {resp.status_code}"
    except httpx.HTTPError as exc:
        healthy = False
        detail = f"unreachable: {exc}"
    await emit(
        "connection.health_checked",
        resource_type="connection",
        resource_id=str(connection_id),
        payload={"healthy": healthy, "detail": detail},
    )
    return HealthStatus(connection_id=connection_id, healthy=healthy, detail=detail)
