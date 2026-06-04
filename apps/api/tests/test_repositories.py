"""Repositories: lifecycle, idempotent version ingestion, and RLS.

DB-gated.
"""

from __future__ import annotations

import uuid

import pytest
from app.context import set_request_context
from app.db import system_session
from app.modules.repositories.api import (
    NormalizedDocument,
    RepositoryCreate,
    create_repository,
    get_documents,
    hard_delete_repository,
    ingest_version,
    list_repositories,
    soft_delete_repository,
)
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _db_available() -> bool:
    try:
        async with system_session() as session:
            await session.execute(text("select 1"))
        return True
    except Exception:
        return False


def _seed_tenant(tenant_id: str) -> None:
    set_request_context(request_id="t", tenant_id=tenant_id, user_id=None)


async def test_create_and_ingest_is_idempotent() -> None:
    if not await _db_available():
        pytest.skip("database not available")

    _seed_tenant(str(uuid.uuid4()))
    repo = await create_repository(RepositoryCreate(name="Reqs"))

    docs = [
        NormalizedDocument(
            source_key="PROJ-1", title="Login", body="As a user...", metadata={}
        ),
        NormalizedDocument(
            source_key="PROJ-2", title="Logout", body="As a user...", metadata={}
        ),
    ]
    v1 = await ingest_version(
        repository_id=repo.id, documents=docs, idempotency_key="sync-1"
    )
    assert v1.version_number == 1
    assert v1.document_count == 2

    # Same idempotency key -> same version, no duplicate.
    v1_again = await ingest_version(
        repository_id=repo.id, documents=docs, idempotency_key="sync-1"
    )
    assert v1_again.id == v1.id

    # New key -> new version.
    v2 = await ingest_version(
        repository_id=repo.id, documents=docs[:1], idempotency_key="sync-2"
    )
    assert v2.version_number == 2
    assert v2.document_count == 1

    stored = await get_documents(v1.id)
    assert {d.source_key for d in stored} == {"PROJ-1", "PROJ-2"}


async def test_soft_then_hard_delete() -> None:
    if not await _db_available():
        pytest.skip("database not available")

    _seed_tenant(str(uuid.uuid4()))
    repo = await create_repository(RepositoryCreate(name="Temp"))

    await soft_delete_repository(repo.id)
    visible = await list_repositories()
    assert repo.id not in {r.id for r in visible}
    assert repo.id in {r.id for r in await list_repositories(include_deleted=True)}

    await hard_delete_repository(repo.id)
    assert repo.id not in {
        r.id for r in await list_repositories(include_deleted=True)
    }


async def test_hard_delete_requires_soft_delete_first() -> None:
    if not await _db_available():
        pytest.skip("database not available")

    _seed_tenant(str(uuid.uuid4()))
    repo = await create_repository(RepositoryCreate(name="Active"))
    with pytest.raises(PermissionError):
        await hard_delete_repository(repo.id)
