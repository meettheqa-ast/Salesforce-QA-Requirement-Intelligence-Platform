"""POST /api/v1/qa/ask: the first user-facing guarded LLM path.

Proves the endpoint runs a versioned prompt through the ai_client chokepoint
with the stub provider, and that budget enforcement returns HTTP 402 when the
tenant cap would be exceeded. DB-gated (metering reads usage from Postgres).
"""

from __future__ import annotations

import uuid

import pytest
from app.db import system_session
from app.main import create_app
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _db_available() -> bool:
    try:
        async with system_session() as session:
            await session.execute(text("select 1"))
        return True
    except Exception:
        return False


async def _dev_token(client: AsyncClient, *, tenant_id: str, role: str) -> str:
    resp = await client.post(
        "/api/v1/auth/dev-token",
        json={
            "user_id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "email": "qa@example.com",
            "role": role,
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def test_ask_returns_stub_answer() -> None:
    if not await _db_available():
        pytest.skip("database not available")

    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token = await _dev_token(
                client, tenant_id=str(uuid.uuid4()), role="qa_engineer"
            )
            resp = await client.post(
                "/api/v1/qa/ask",
                headers={"authorization": f"Bearer {token}"},
                json={"question": "What requirements lack acceptance criteria?"},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["is_stub"] is True
    assert body["prompt_id"] == "qa.answer"
    assert body["prompt_version"] == 1
    assert body["output_tokens"] > 0


async def test_ask_requires_auth() -> None:
    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/qa/ask", json={"question": "hi"}
            )
    assert resp.status_code == 401


async def test_ask_over_budget_returns_402(monkeypatch: pytest.MonkeyPatch) -> None:
    if not await _db_available():
        pytest.skip("database not available")

    # The stub provider is free, so a real budget would never trip. Force the
    # pre-call gate to report "over budget" to exercise the 402 path that a real
    # provider with a low cap would hit in production.
    from app.modules.ai_client._internal import service as ai_service

    async def _always_over(_estimated_cost_cents: float) -> bool:
        return False

    monkeypatch.setattr(ai_service, "check_budget", _always_over)

    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            token = await _dev_token(
                client, tenant_id=str(uuid.uuid4()), role="qa_engineer"
            )
            resp = await client.post(
                "/api/v1/qa/ask",
                headers={"authorization": f"Bearer {token}"},
                json={"question": "anything", "max_tokens": 256},
            )

    assert resp.status_code == 402
    assert "budget" in resp.json()["detail"].lower()
