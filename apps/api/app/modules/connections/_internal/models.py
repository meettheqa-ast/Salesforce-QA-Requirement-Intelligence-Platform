"""Connection ORM model.

A Connection stores how to reach an external system (e.g. Jira Cloud) plus its
credentials, sealed at rest via envelope encryption. The plaintext credential
NEVER touches the database or logs. Tenant-scoped + RLS.
"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models_common import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ConnectionType(StrEnum):
    JIRA_CLOUD = "jira_cloud"


class AuthType(StrEnum):
    # Jira Cloud uses email + API token (HTTP Basic). Other types added later.
    API_TOKEN = "api_token"


class ConnectionStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class Connection(
    UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, Base
):
    __tablename__ = "connections"

    name: Mapped[str] = mapped_column(nullable=False)
    connection_type: Mapped[str] = mapped_column(
        nullable=False, default=ConnectionType.JIRA_CLOUD.value
    )
    base_url: Mapped[str] = mapped_column(nullable=False)
    auth_type: Mapped[str] = mapped_column(
        nullable=False, default=AuthType.API_TOKEN.value
    )
    # Non-secret principal (e.g. the Jira account email). Safe to store in clear.
    principal: Mapped[str] = mapped_column(nullable=False, default="")
    # Sealed credential envelope (base64). Opened ONLY by this module's service.
    sealed_secret: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        nullable=False, default=ConnectionStatus.ACTIVE.value
    )
