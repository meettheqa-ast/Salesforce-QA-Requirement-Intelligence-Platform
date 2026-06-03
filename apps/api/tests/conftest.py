"""Shared pytest fixtures.

These tests run against stub providers and DO NOT require a database unless a
test explicitly opts in via the `db` marker (wired in Sprint 1 acceptance).
"""

from __future__ import annotations

import os

# Force stub providers for the whole test session before settings load.
os.environ.setdefault("AI_PROVIDER", "stub")
os.environ.setdefault("EMBEDDINGS_PROVIDER", "stub")
os.environ.setdefault("JIRA_PROVIDER", "stub")
os.environ.setdefault("AUTH_PROVIDER", "dev")
os.environ.setdefault("APP_ENV", "local")

import pytest
import pytest_asyncio
from app.context import set_request_context


@pytest.fixture(autouse=True)
def _request_context() -> None:
    """Seed a deterministic request context so tenant-scoped code has a tenant."""
    set_request_context(
        request_id="test-request",
        tenant_id="00000000-0000-0000-0000-000000000001",
        user_id="00000000-0000-0000-0000-0000000000aa",
    )


@pytest_asyncio.fixture(autouse=True)
async def _reset_engine():
    """Dispose the cached async engine around each test.

    pytest-asyncio runs each test in its own event loop. The module-level engine
    pools connections bound to the loop that created them, so without disposal a
    later test inherits connections tied to a closed loop (seen as
    'coroutine Connection._cancel was never awaited'). Resetting per test keeps
    every test's DB access on its own live loop.
    """
    import app.db as db

    db._engine = None
    db._session_factory = None
    yield
    if db._engine is not None:
        await db._engine.dispose()
    db._engine = None
    db._session_factory = None
