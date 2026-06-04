"""HTTP routes for the repositories module."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.api import Principal, require_role

from . import service
from .schemas import (
    RepositoryCreate,
    RepositoryDocumentOut,
    RepositoryOut,
    RepositoryVersionOut,
)

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
