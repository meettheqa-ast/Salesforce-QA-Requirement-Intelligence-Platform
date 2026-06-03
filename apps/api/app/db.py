"""Database engine, session factory, and the declarative base.

The critical function here is `tenant_session`: it opens a transaction and
issues `SET LOCAL app.current_tenant_id = '<uuid>'` so that Postgres Row-Level
Security policies (see migrations) restrict every query to the current tenant.
This is the enforced backstop described in DECISIONS.md D-0010.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.context import current_tenant_id
from app.settings import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models across modules."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


@asynccontextmanager
async def tenant_session(
    tenant_id: str | None = None,
) -> AsyncIterator[AsyncSession]:
    """Yield a session with RLS scoped to the given (or current) tenant.

    If no tenant is available, the session runs without a tenant GUC set;
    RLS policies will then return zero rows for tenant-scoped tables, which is
    the safe default. Admin/system operations that legitimately span tenants
    must use `system_session` and emit explicit audit events.
    """
    resolved = tenant_id or current_tenant_id()
    factory = get_session_factory()
    async with factory() as session, session.begin():
        if resolved is not None:
            # Postgres SET does not accept bind params; set_config() does and is
            # injection-safe. Third arg `true` scopes it to the transaction
            # (equivalent to SET LOCAL).
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": resolved},
            )
        yield session


@asynccontextmanager
async def system_session() -> AsyncIterator[AsyncSession]:
    """Yield a session WITHOUT tenant scoping. For migrations, onboarding, and
    cross-tenant admin paths only. Callers must emit audit events.
    """
    factory = get_session_factory()
    async with factory() as session, session.begin():
        await session.execute(
            text("SELECT set_config('app.bypass_rls', 'on', true)")
        )
        yield session
