"""The app must construct and serve health endpoints without a database."""

from __future__ import annotations

import pytest
from app.main import create_app
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_healthz() -> None:
    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_dev_token_and_whoami() -> None:
    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            minted = await client.post(
                "/api/v1/auth/dev-token",
                json={
                    "user_id": "00000000-0000-0000-0000-0000000000aa",
                    "tenant_id": "00000000-0000-0000-0000-000000000001",
                    "role": "tenant_admin",
                },
            )
            assert minted.status_code == 200
            token = minted.json()["access_token"]

            me = await client.get(
                "/api/v1/auth/me",
                headers={"authorization": f"Bearer {token}"},
            )
    assert me.status_code == 200
    body = me.json()
    assert body["role"] == "tenant_admin"
    assert body["tenant_id"] == "00000000-0000-0000-0000-000000000001"
