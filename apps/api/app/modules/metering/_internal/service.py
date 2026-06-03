"""Usage recording and budget checks.

Budget enforcement is intentionally simple for MVP: sum the current month's
cost for a tenant and compare against the configured cap. The check happens
before the LLM call (in ai_client) so an over-budget tenant never spends more.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.context import require_tenant_id
from app.db import system_session
from app.settings import get_settings

from .models import UsageMeter


def _current_period() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


async def record_usage(
    *, model: str, input_tokens: int, output_tokens: int, cost_cents: float
) -> None:
    tenant_id = uuid.UUID(require_tenant_id())
    period = _current_period()
    async with system_session() as session:
        stmt = insert(UsageMeter).values(
            tenant_id=tenant_id,
            period_month=period,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_cents=cost_cents,
            request_count=1,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_usage_period_model",
            set_={
                "input_tokens": UsageMeter.input_tokens + input_tokens,
                "output_tokens": UsageMeter.output_tokens + output_tokens,
                "cost_cents": UsageMeter.cost_cents + cost_cents,
                "request_count": UsageMeter.request_count + 1,
            },
        )
        await session.execute(stmt)


async def current_month_cost_cents(tenant_id: uuid.UUID | None = None) -> float:
    tid = tenant_id or uuid.UUID(require_tenant_id())
    period = _current_period()
    async with system_session() as session:
        result = await session.execute(
            select(func.coalesce(func.sum(UsageMeter.cost_cents), 0)).where(
                UsageMeter.tenant_id == tid,
                UsageMeter.period_month == period,
            )
        )
        return float(result.scalar_one())


async def check_budget(estimated_cost_cents: float) -> bool:
    """Return True if the estimated additional spend is within budget."""
    settings = get_settings()
    cap = settings.default_tenant_monthly_budget_cents
    spent = await current_month_cost_cents()
    return (spent + estimated_cost_cents) <= cap
