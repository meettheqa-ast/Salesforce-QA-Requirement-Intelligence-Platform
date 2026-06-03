"""Usage meter ORM model. One row per (tenant, period, model) rollup."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models_common import TimestampMixin, UUIDPrimaryKeyMixin


class UsageMeter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "usage_meter"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "period_month", "model", name="uq_usage_period_model"
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, index=True
    )
    period_month: Mapped[str] = mapped_column(nullable=False)  # YYYY-MM
    model: Mapped[str] = mapped_column(nullable=False)
    input_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    output_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    cost_cents: Mapped[float] = mapped_column(Numeric(14, 6), default=0)
    request_count: Mapped[int] = mapped_column(BigInteger, default=0)
