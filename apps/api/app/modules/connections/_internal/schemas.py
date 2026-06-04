"""DTOs for the connections module.

ConnectionOut deliberately omits the secret. There is NO schema that serializes
a decrypted credential to an API response; credentials are returned only to
in-process callers via get_credentials_for_use().
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from .models import AuthType, ConnectionType


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    connection_type: ConnectionType = ConnectionType.JIRA_CLOUD
    base_url: str = Field(min_length=1)
    auth_type: AuthType = AuthType.API_TOKEN
    principal: str = Field(default="", max_length=320)
    # The plaintext credential (e.g. Jira API token). Sealed immediately; never
    # stored or echoed back.
    secret: str = Field(min_length=1, repr=False)


class ConnectionOut(BaseModel):
    id: uuid.UUID
    name: str
    connection_type: str
    base_url: str
    auth_type: str
    principal: str
    status: str

    model_config = {"from_attributes": True}


class HealthStatus(BaseModel):
    connection_id: uuid.UUID
    healthy: bool
    detail: str
