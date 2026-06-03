"""Public API of the connections module (Sprint 2).

Planned surface:
  - create_connection(name, base_url, auth_type, credentials) -> ConnectionOut
  - get_credentials_for_use(connection_id) -> decrypted, scoped, audited
  - check_health(connection_id) -> HealthStatus

This is the ONLY module that decrypts secrets. Envelope encryption via KMS.
Implemented in Sprint 2 (Repository + Jira Integration).
"""

from __future__ import annotations

__all__: list[str] = []
