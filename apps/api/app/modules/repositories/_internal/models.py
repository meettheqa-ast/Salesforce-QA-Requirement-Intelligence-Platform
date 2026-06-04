"""Repository, version, document, and chunk ORM models.

A Repository is a tenant's logical workspace for a set of requirements ingested
from a source (e.g. a Jira project). Each ingestion produces a RepositoryVersion
(an immutable snapshot), which contains RepositoryDocuments (normalized stories).
RepositoryDocumentChunk holds embedding-ready slices; the chunking LOGIC is a
Sprint 3 (RAG) concern -- the table exists now so the schema is stable, but no
code populates it yet.

All tables are tenant-scoped and protected by RLS (see the migration).
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models_common import TenantScopedMixin, TimestampMixin, UUIDPrimaryKeyMixin


class RepositoryStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"  # soft-deleted; rows retained until hard-delete


class RepositorySourceType(StrEnum):
    JIRA = "jira"
    MANUAL = "manual"


class VersionStatus(StrEnum):
    PENDING = "pending"
    SYNCING = "syncing"
    READY = "ready"
    FAILED = "failed"


class Repository(
    UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, Base
):
    __tablename__ = "repositories"

    name: Mapped[str] = mapped_column(nullable=False)
    source_type: Mapped[str] = mapped_column(
        nullable=False, default=RepositorySourceType.JIRA.value
    )
    # Optional link to the connection used to sync this repository.
    connection_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        nullable=False, default=RepositoryStatus.ACTIVE.value
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )


class RepositoryVersion(
    UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, Base
):
    __tablename__ = "repository_versions"
    __table_args__ = (
        UniqueConstraint(
            "repository_id", "version_number", name="uq_repo_version_number"
        ),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        nullable=False, default=VersionStatus.PENDING.value
    )
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Idempotency: a sync job stamps this so re-running with the same key is a
    # no-op rather than producing a duplicate version.
    sync_idempotency_key: Mapped[str | None] = mapped_column(
        nullable=True, index=True
    )


class RepositoryDocument(
    UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, Base
):
    __tablename__ = "repository_documents"
    __table_args__ = (
        UniqueConstraint(
            "version_id", "source_key", name="uq_repo_doc_source_key"
        ),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("repository_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The canonical, normalized story. `source_key` is the upstream id (e.g. the
    # Jira issue key) and is unique within a version.
    source_key: Mapped[str] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    doc_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )


class RepositoryDocumentChunk(
    UUIDPrimaryKeyMixin, TimestampMixin, TenantScopedMixin, Base
):
    """Embedding-ready slice of a document.

    Created now for schema stability; populated by the RAG module in Sprint 3.
    The embedding vector column is added in the Sprint 3 migration to avoid
    committing to a dimension before the embeddings provider is chosen.
    """

    __tablename__ = "repository_document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("repository_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
