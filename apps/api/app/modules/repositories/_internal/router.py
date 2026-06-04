"""HTTP routes for the repositories module."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.context import require_tenant_id
from app.modules.auth.api import Principal, require_role
from app.modules.jobs.api import submit

from . import service
from .schemas import (
    RepositoryCreate,
    RepositoryDocumentOut,
    RepositoryOut,
    RepositoryVersionOut,
)


class SyncAccepted(BaseModel):
    repository_id: uuid.UUID
    job_id: str | None
    idempotency_key: str

router = APIRouter(prefix="/repositories", tags=["repositories"])

_MANAGE = ("tenant_admin", "qa_lead")
_VIEW = ("tenant_admin", "qa_lead", "qa_engineer")


@router.post("", response_model=RepositoryOut, status_code=201)
async def create_repository(
    data: RepositoryCreate,
    _p: Principal = Depends(require_role(*_MANAGE)),
) -> RepositoryOut:
    return await service.create_repository(data)


@router.get("", response_model=list[RepositoryOut])
async def list_repositories(
    include_deleted: bool = False,
    _p: Principal = Depends(require_role(*_VIEW)),
) -> list[RepositoryOut]:
    return await service.list_repositories(include_deleted=include_deleted)


@router.get("/{repository_id}", response_model=RepositoryOut)
async def get_repository(
    repository_id: uuid.UUID,
    _p: Principal = Depends(require_role(*_VIEW)),
) -> RepositoryOut:
    repo = await service.get_repository(repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.post("/{repository_id}/archive", response_model=RepositoryOut)
async def archive_repository(
    repository_id: uuid.UUID,
    _p: Principal = Depends(require_role(*_MANAGE)),
) -> RepositoryOut:
    try:
        return await service.archive_repository(repository_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{repository_id}", response_model=RepositoryOut)
async def soft_delete_repository(
    repository_id: uuid.UUID,
    _p: Principal = Depends(require_role(*_MANAGE)),
) -> RepositoryOut:
    try:
        return await service.soft_delete_repository(repository_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{repository_id}/purge", status_code=204)
async def hard_delete_repository(
    repository_id: uuid.UUID,
    _p: Principal = Depends(require_role("tenant_admin")),
) -> None:
    try:
        await service.hard_delete_repository(repository_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{repository_id}/sync", response_model=SyncAccepted, status_code=202)
async def trigger_sync(
    repository_id: uuid.UUID,
    _p: Principal = Depends(require_role(*_MANAGE)),
) -> SyncAccepted:
    """Enqueue a background Jira sync for this repository.

    A fresh idempotency key per request means each manual sync produces a new
    version; retries of the SAME enqueued job (same key) are deduplicated by
    the jobs runtime.
    """
    repo = await service.get_repository(repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    tenant_id = require_tenant_id()
    idempotency_key = f"{repository_id}:{datetime.now(UTC).isoformat()}"
    job_id = await submit(
        "sync_repository_job",
        tenant_id=tenant_id,
        repository_id=str(repository_id),
        connection_id=str(repo.connection_id) if repo.connection_id else None,
        idempotency_key=idempotency_key,
        dedup_key=idempotency_key,
    )
    return SyncAccepted(
        repository_id=repository_id, job_id=job_id, idempotency_key=idempotency_key
    )


@router.get("/{repository_id}/versions", response_model=list[RepositoryVersionOut])
async def list_versions(
    repository_id: uuid.UUID,
    _p: Principal = Depends(require_role(*_VIEW)),
) -> list[RepositoryVersionOut]:
    return await service.list_versions(repository_id)


@router.get(
    "/{repository_id}/versions/{version_id}/documents",
    response_model=list[RepositoryDocumentOut],
)
async def get_documents(
    repository_id: uuid.UUID,
    version_id: uuid.UUID,
    _p: Principal = Depends(require_role(*_VIEW)),
) -> list[RepositoryDocumentOut]:
    return await service.get_documents(version_id)
