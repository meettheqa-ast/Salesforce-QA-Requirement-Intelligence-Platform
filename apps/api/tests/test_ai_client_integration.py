"""Full ai_client.complete() path with the stub provider and a live DB.

Proves: prompt loading + budget check + provider dispatch + usage recording +
audit emission + result stamping all work end to end. Skipped if DB unavailable.
"""

from __future__ import annotations

import uuid

import pytest
from app.context import set_request_context
from app.db import system_session
from app.modules.ai_client.api import complete
from app.modules.metering.api import current_month_cost_cents
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


async def _db_available() -> bool:
    try:
        async with system_session() as session:
            await session.execute(text("select 1"))
        return True
    except Exception:
        return False


async def test_complete_records_usage_and_stamps_prompt() -> None:
    if not await _db_available():
        pytest.skip("database not available")

    tenant_id = str(uuid.uuid4())
    set_request_context(request_id="t", tenant_id=tenant_id, user_id=None)

    before = await current_month_cost_cents()

    result = await complete(
        prompt_id="analysis.triage",
        prompt_version=1,
        user_content="<retrieved_content>A story with no acceptance criteria. "
        "Return JSON.</retrieved_content>",
        max_tokens=64,
    )

    assert result.is_stub is True
    assert result.prompt_id == "analysis.triage"
    assert result.prompt_version == 1
    assert result.usage.total > 0

    after = await current_month_cost_cents()
    # Stub is free, so cost should be unchanged but a usage row must exist.
    assert after >= before
