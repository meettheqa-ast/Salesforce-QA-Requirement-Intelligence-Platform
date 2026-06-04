"""DTOs for the repositories module public API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from .models import RepositorySourceType


class RepositoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_type: RepositorySourceType = RepositorySourceType.JIRA
    connection_id: uuid.UUID | None = None


class RepositoryOut(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str
    connection_id: uuid.UUID | None
    status: str

    model_config = {"from_attributes": True}


class RepositoryVersionOut(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    version_number: int
    status: str
    document_count: int

    model_config = {"from_attributes": True}


class RepositoryDocumentOut(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    version_id: uuid.UUID
    source_key: str
    title: str
    body: str

    model_config = {"from_attributes": True}
