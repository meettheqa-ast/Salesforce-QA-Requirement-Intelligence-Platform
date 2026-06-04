"""Sprint 2: connections, repositories, versions, documents, chunks + RLS.

Revision ID: 0002_connections_repositories
Revises: 0001_initial
Create Date: 2026-06-04

All five tables are tenant-scoped and get the same RLS policy as Sprint 0
tenant tables: visible when the bypass GUC is on, or when tenant_id matches the
per-request app.current_tenant_id GUC. The chunks table is created here for
schema stability; the embedding vector column is deferred to the Sprint 3 (RAG)
migration so we don't commit to a dimension before choosing the provider.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_connections_repositories"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_TABLES = (
    "connections",
    "repositories",
    "repository_versions",
    "repository_documents",
    "repository_document_chunks",
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "connections",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("connection_type", sa.String(), nullable=False,
                  server_default="jira_cloud"),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("auth_type", sa.String(), nullable=False,
                  server_default="api_token"),
        sa.Column("principal", sa.String(), nullable=False, server_default=""),
        sa.Column("sealed_secret", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        *_timestamps(),
    )
    op.create_index("ix_connections_tenant_id", "connections", ["tenant_id"])

    op.create_table(
        "repositories",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False, server_default="jira"),
        sa.Column("connection_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("settings", sa.dialects.postgresql.JSONB(), nullable=False,
                  server_default="{}"),
        *_timestamps(),
    )
    op.create_index("ix_repositories_tenant_id", "repositories", ["tenant_id"])
    op.create_index("ix_repositories_connection_id", "repositories",
                    ["connection_id"])

    op.create_table(
        "repository_versions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(),
                  sa.ForeignKey("repositories.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("document_count", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("sync_idempotency_key", sa.String(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("repository_id", "version_number",
                            name="uq_repo_version_number"),
    )
    op.create_index("ix_repository_versions_tenant_id", "repository_versions",
                    ["tenant_id"])
    op.create_index("ix_repository_versions_repository_id", "repository_versions",
                    ["repository_id"])
    op.create_index("ix_repository_versions_sync_idempotency_key",
                    "repository_versions", ["sync_idempotency_key"])

    op.create_table(
        "repository_documents",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("repository_id", sa.UUID(),
                  sa.ForeignKey("repositories.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("version_id", sa.UUID(),
                  sa.ForeignKey("repository_versions.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("source_key", sa.String(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("doc_metadata", sa.dialects.postgresql.JSONB(), nullable=False,
                  server_default="{}"),
        *_timestamps(),
        sa.UniqueConstraint("version_id", "source_key",
                            name="uq_repo_doc_source_key"),
    )
    op.create_index("ix_repository_documents_tenant_id", "repository_documents",
                    ["tenant_id"])
    op.create_index("ix_repository_documents_repository_id",
                    "repository_documents", ["repository_id"])
    op.create_index("ix_repository_documents_version_id", "repository_documents",
                    ["version_id"])

    op.create_table(
        "repository_document_chunks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(),
                  sa.ForeignKey("repository_documents.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        *_timestamps(),
    )
    op.create_index("ix_repository_document_chunks_tenant_id",
                    "repository_document_chunks", ["tenant_id"])
    op.create_index("ix_repository_document_chunks_document_id",
                    "repository_document_chunks", ["document_id"])

    # --- Row-Level Security -------------------------------------------------
    _bypass = "current_setting('app.bypass_rls', true) = 'on'"
    _tenant_match = "tenant_id = current_setting('app.current_tenant_id', true)::uuid"
    for table in _TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            f"USING ({_bypass} OR {_tenant_match}) "
            f"WITH CHECK ({_bypass} OR {_tenant_match})"
        )


def downgrade() -> None:
    for table in _TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("repository_document_chunks")
    op.drop_table("repository_documents")
    op.drop_table("repository_versions")
    op.drop_table("repositories")
    op.drop_table("connections")
