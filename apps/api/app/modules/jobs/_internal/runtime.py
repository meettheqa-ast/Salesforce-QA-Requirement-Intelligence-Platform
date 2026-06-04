"""arq-based background job runtime.

Sprint 0 ships a no-op job to prove the queue round-trips and that idempotency
keys are honored. Real jobs (Jira sync, analysis, generation) land in later
sprints. The `submit` function is the stable interface other modules use; the
arq WorkerSettings below is the worker entrypoint.
"""

from __future__ import annotations

from typing import Any

from arq import create_pool
from arq.connections import RedisSettings

from app.context import set_request_context
from app.logging import get_logger
from app.settings import get_settings

log = get_logger(__name__)


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def noop_job(_ctx: dict[str, Any], message: str) -> str:
    """Trivial job used to validate the queue in Sprint 0."""
    log.info("jobs.noop", message=message)
    return f"processed:{message}"


async def sync_repository_job(
    _ctx: dict[str, Any],
    *,
    tenant_id: str,
    repository_id: str,
    connection_id: str | None,
    idempotency_key: str,
) -> str:
    """Background Jira sync. Runs outside an HTTP request, so it establishes the
    tenant context itself before delegating to the jira module (which calls the
    audited credential path and the repositories ingestion API).
    """
    import uuid

    from app.modules.jira.api import sync_repository

    set_request_context(request_id=f"job:{idempotency_key}", tenant_id=tenant_id,
                        user_id=None)
    version_id = await sync_repository(
        repository_id=uuid.UUID(repository_id),
        connection_id=uuid.UUID(connection_id) if connection_id else None,
        idempotency_key=idempotency_key,
    )
    log.info("jobs.sync_repository", repository_id=repository_id,
             version_id=str(version_id))
    return str(version_id)


async def submit(
    job_name: str, *args: Any, dedup_key: str | None = None, **kwargs: Any
) -> str | None:
    """Enqueue a job. `dedup_key` maps to arq's job_id for idempotency:
    enqueuing the same key while a prior job is pending is a no-op.
    """
    pool = await create_pool(_redis_settings())
    try:
        job = await pool.enqueue_job(job_name, *args, _job_id=dedup_key, **kwargs)
        return job.job_id if job else None
    finally:
        await pool.close()


class WorkerSettings:
    """arq worker entrypoint. Run with: arq app.modules.jobs._internal.runtime.WorkerSettings"""

    functions = [noop_job, sync_repository_job]
    redis_settings = _redis_settings()
