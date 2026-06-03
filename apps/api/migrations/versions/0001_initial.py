"""Initial schema: tenants, users, memberships, audit_events, usage_meter + RLS.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-03

RLS model:
  - Tenant-scoped tables (usage_meter) get a policy comparing tenant_id to the
    `app.current_tenant_id` GUC set per request in app.db.tenant_session.
  - A `app.bypass_rls` GUC lets system_session (onboarding, admin) bypass.
  - audit_events has a nullable tenant_id; its policy allows rows where tenant
    matches OR where the bypass GUC is on (so null-tenant system events persist).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False, server_default="pooled"),
        sa.Column("region", sa.String(), nullable=False, server_default="us-east-1"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("settings", sa.dialects.postgresql.JSONB(), nullable=False,
                  server_default="{}"),
        sa.Column("kms_key_alias", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("sso_subject", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_sso_subject", "users", ["sso_subject"])

    op.create_table(
        "memberships",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.UUID(),
                  sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="qa_engineer"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_index("ix_memberships_tenant_id", "memberships", ["tenant_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=False,
                  server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])

    op.create_table(
        "usage_meter",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("period_month", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.BigInteger(), server_default="0"),
        sa.Column("output_tokens", sa.BigInteger(), server_default="0"),
        sa.Column("cost_cents", sa.Numeric(14, 6), server_default="0"),
        sa.Column("request_count", sa.BigInteger(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "period_month", "model",
                            name="uq_usage_period_model"),
    )
    op.create_index("ix_usage_meter_tenant_id", "usage_meter", ["tenant_id"])

    # --- Row-Level Security -------------------------------------------------
    # Helper: a row is visible if bypass is on, or tenant matches the GUC.
    _bypass = "current_setting('app.bypass_rls', true) = 'on'"
    _tenant_match = "tenant_id = current_setting('app.current_tenant_id', true)::uuid"

    for table in ("usage_meter",):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            f"USING ({_bypass} OR {_tenant_match}) "
            f"WITH CHECK ({_bypass} OR {_tenant_match})"
        )

    # audit_events: nullable tenant. Visible when bypass, or tenant matches.
    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY audit_events_tenant_isolation ON audit_events "
        f"USING ({_bypass} OR {_tenant_match}) "
        f"WITH CHECK ({_bypass} OR tenant_id IS NULL OR {_tenant_match})"
    )


def downgrade() -> None:
    for table in ("audit_events", "usage_meter"):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("usage_meter")
    op.drop_table("audit_events")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("tenants")
