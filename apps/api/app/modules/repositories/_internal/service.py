"""Repository lifecycle + document storage.

Repositories and their versions/documents are tenant-scoped; all access uses
tenant_session so RLS applies. Versions are immutable snapshots produced by an
ingestion run. `ingest_version` is idempotent on (repository, idempotency_key):
re-running a sync with the same key returns the existing version instead of
creating a duplicate.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select

from app.context import require_tenant_id
from app.db import tenant_session
from app.modules.audit.api import emit

from .models import (
    Repository,
    RepositoryDocument,
    RepositoryStatus,
    RepositoryVersion,
    VersionStatus,
)
from .schemas import (
    RepositoryCreate,
    RepositoryDocumentOut,
    RepositoryOut,
    RepositoryVersionOut,
)


@dataclass(frozen=True, slots=True)
class NormalizedDocument:
    """A canonical story produced by a source adapter (e.g. jira)."""

    source_key: str
    title: str
    body: str
    metadata: dict[str, Any]


async def create_repository(data: RepositoryCreate) -> RepositoryOut:
    tenant_id = uuid.UUID(require_tenant_id())
    async with tenant_session() as session:
        repo = Repository(
            tenant_id=tenant_id,
            name=data.name,
            source_type=data.source_type.value,
            connection_id=data.connection_id,
        )
        session.add(repo)
        await session.flush()
        out = RepositoryOut.model_validate(repo)
    await emit(
        "repository.created",
        resource_type="repository",
        resource_id=str(out.id),
        payload={"source_type": out.source_type},
    )
    return out


async def get_repository(repository_id: uuid.UUID) -> RepositoryOut | None:
    async with tenant_session() as session:
        repo = await session.get(Repository, repository_id)
        return RepositoryOut.model_validate(repo) if repo else None


async def list_repositories(*, include_deleted: bool = False) -> list[RepositoryOut]:
    async with tenant_session() as session:
        stmt = select(Repository).order_by(Repository.created_at)
        if not include_deleted:
            stmt = stmt.where(Repository.status != RepositoryStatus.DELETED.value)
        result = await session.execute(stmt)
        return [RepositoryOut.model_validate(r) for r in result.scalars().all()]


async def _set_status(
    repository_id: uuid.UUID, status: RepositoryStatus, action: str
) -> RepositoryOut:
    async with tenant_session() as session:
        repo = await session.get(Repository, repository_id)
        if repo is None:
            raise LookupError(f"Repository {repository_id} not found")
        repo.status = status.value
        await session.flush()
        out = RepositoryOut.model_validate(repo)
    await emit(action, resource_type="repository", resource_id=str(repository_id))
    return out


async def archive_repository(repository_id: uuid.UUID) -> RepositoryOut:
    return await _set_status(
        repository_id, RepositoryStatus.ARCHIVED, "repository.archived"
    )


async def soft_delete_repository(repository_id: uuid.UUID) -> RepositoryOut:
    return await _set_status(
        repository_id, RepositoryStatus.DELETED, "repository.soft_deleted"
    )


async def hard_delete_repository(repository_id: uuid.UUID) -> None:
    """Permanently remove a soft-deleted repository and its cascade children."""
    async with tenant_session() as session:
        repo = await session.get(Repository, repository_id)
        if repo is None:
            raise LookupError(f"Repository {repository_id} not found")
        if repo.status != RepositoryStatus.DELETED.value:
            raise PermissionError(
                "Repository must be soft-deleted before hard-delete"
            )
        await session.delete(repo)
    await emit(
        "repository.hard_deleted",
        resource_type="repository",
        resource_id=str(repository_id),
    )


async def ingest_version(
    *,
    repository_id: uuid.UUID,
    documents: list[NormalizedDocument],
    idempotency_key: str,
) -> RepositoryVersionOut:
    """Create a new READY version with the given documents, idempotently.

    If a version with the same idempotency_key already exists for this
    repository, it is returned unchanged (the sync was already applied).
    """
    async with tenant_session() as session:
        repo = await session.get(Repository, repository_id)
        if repo is None:
            raise LookupError(f"Repository {repository_id} not found")

        existing = (
            await session.execute(
                select(RepositoryVersion).where(
                    RepositoryVersion.repository_id == repository_id,
                    RepositoryVersion.sync_idempotency_key == idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return RepositoryVersionOut.model_validate(existing)

        next_number = (
            await session.execute(
                select(func.coalesce(func.max(RepositoryVersion.version_number), 0))
                .where(RepositoryVersion.repository_id == repository_id)
            )
        ).scalar_one() + 1

        version = RepositoryVersion(
            tenant_id=repo.tenant_id,
            repository_id=repository_id,
            version_number=next_number,
            status=VersionStatus.READY.value,
            document_count=len(documents),
            sync_idempotency_key=idempotency_key,
        )
        session.add(version)
        await session.flush()

        for doc in documents:
            session.add(
                RepositoryDocument(
                    tenant_id=repo.tenant_id,
                    repository_id=repository_id,
                    version_id=version.id,
                    source_key=doc.source_key,
                    title=doc.title,
                    body=doc.body,
                    doc_metadata=doc.metadata,
                )
            )
        await session.flush()
        out = RepositoryVersionOut.model_validate(version)

    await emit(
        "repository.version_ingested",
        resource_type="repository_version",
        resource_id=str(out.id),
        payload={
            "repository_id": str(repository_id),
            "version_number": out.version_number,
            "document_count": out.document_count,
        },
    )
    return out


async def list_versions(repository_id: uuid.UUID) -> list[RepositoryVersionOut]:
    async with tenant_session() as session:
        result = await session.execute(
            select(RepositoryVersion)
            .where(RepositoryVersion.repository_id == repository_id)
            .order_by(RepositoryVersion.version_number)
        )
        return [RepositoryVersionOut.model_validate(v) for v in result.scalars().all()]


async def get_documents(version_id: uuid.UUID) -> list[RepositoryDocumentOut]:
    async with tenant_session() as session:
        result = await session.execute(
            select(RepositoryDocument)
            .where(RepositoryDocument.version_id == version_id)
            .order_by(RepositoryDocument.source_key)
        )
        return [RepositoryDocumentOut.model_validate(d) for d in result.scalars().all()]
