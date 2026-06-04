"""End-to-end ingestion: stub Jira -> normalize -> repository documents.

Plus pure normalization unit tests (no DB) for ADF and acceptance-criteria
extraction.
"""

from __future__ import annotations

import uuid

import pytest
from app.context import set_request_context
from app.db import system_session
from app.modules.jira._internal.types import JiraIssue
from app.modules.jira.api import normalize_issue, sync_repository
from app.modules.repositories.api import (
    RepositoryCreate,
    create_repository,
    get_documents,
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


async def test_normalize_plain_text_with_acceptance_criteria() -> None:
    issue = JiraIssue(
        key="X-1",
        fields={
            "summary": "Login",
            "description": (
                "As a user I log in.\n"
                "Acceptance Criteria:\n"
                "- Valid creds work\n"
                "- Bad creds error\n"
            ),
            "issuetype": {"name": "Story"},
            "status": {"name": "To Do"},
            "labels": ["auth"],
        },
    )
    story = normalize_issue(issue)
    assert story.title == "Login"
    assert story.issue_type == "Story"
    assert story.acceptance_criteria == ["Valid creds work", "Bad creds error"]


async def test_normalize_adf_description() -> None:
    issue = JiraIssue(
        key="X-2",
        fields={
            "summary": "Reset",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Reset via link."}],
                    }
                ],
            },
        },
    )
    story = normalize_issue(issue)
    assert "Reset via link." in story.body


async def test_stub_sync_populates_repository_documents() -> None:
    if not await _db_available():
        pytest.skip("database not available")

    set_request_context(request_id="t", tenant_id=str(uuid.uuid4()), user_id=None)
    repo = await create_repository(RepositoryCreate(name="Ingested"))

    version_id = await sync_repository(
        repository_id=repo.id,
        connection_id=None,  # stub ignores credentials
        idempotency_key="e2e-1",
    )

    docs = await get_documents(version_id)
    keys = {d.source_key for d in docs}
    assert keys == {"DEMO-1", "DEMO-2", "DEMO-3"}
    # The ADF-described issue normalized to readable text.
    demo2 = next(d for d in docs if d.source_key == "DEMO-2")
    assert "reset link" in demo2.body.lower()


async def test_stub_sync_is_idempotent() -> None:
    if not await _db_available():
        pytest.skip("database not available")

    set_request_context(request_id="t", tenant_id=str(uuid.uuid4()), user_id=None)
    repo = await create_repository(RepositoryCreate(name="IdemSync"))

    v1 = await sync_repository(
        repository_id=repo.id, connection_id=None, idempotency_key="same"
    )
    v2 = await sync_repository(
        repository_id=repo.id, connection_id=None, idempotency_key="same"
    )
    assert v1 == v2
