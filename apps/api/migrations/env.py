"""Alembic environment.

Imports every module's models so `Base.metadata` is complete, then runs
migrations online against the async engine (converted to sync URL for Alembic).
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from app.db import Base

# Import models so they register on Base.metadata. Keep this list in sync with
# modules that own tables.
from app.modules.audit._internal import models as _audit_models  # noqa: F401
from app.modules.metering._internal import models as _metering_models  # noqa: F401
from app.modules.tenants._internal import models as _tenants_models  # noqa: F401
from app.settings import get_settings
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    # Migrations run as the superuser role so they can create tables, extensions,
    # and RLS policies. The application uses the restricted role at runtime.
    return get_settings().migration_database_url


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    raise SystemExit("Offline migrations are not supported for this project.")
run_migrations_online()
