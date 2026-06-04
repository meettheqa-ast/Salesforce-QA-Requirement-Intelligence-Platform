"""Public API of the connections module (Sprint 2).

Planned surface:
  - create_connection(name, base_url, auth_type, credentials) -> ConnectionOut
  - get_credentials_for_use(connection_id) -> decrypted, scoped, audited
  - check_health(connection_id) -> HealthStatus

This is the ONLY module that decrypts secrets. Envelope encryption via KMS.
Implemented in Sprint 2 (Repository + Jira Integration).
"""

from __future__ import annotations

from app.modules.connections._internal.router import router
from app.modules.connections._internal.schemas import (
    ConnectionCreate,
    ConnectionOut,
    HealthStatus,
)
from app.modules.connections._internal.service import (
    UsableCredentials,
    check_health,
    create_connection,
    get_connection,
    get_credentials_for_use,
    list_connections,
)

__all__ = [
    "ConnectionCreate",
    "ConnectionOut",
    "HealthStatus",
    "UsableCredentials",
    "check_health",
    "create_connection",
    "get_connection",
    "get_credentials_for_use",
    "list_connections",
    "router",
]
