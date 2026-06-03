"""FastAPI application factory and entrypoint.

Wires middleware, lifespan, health endpoints, and module routers. Routers are
mounted from each module's public api package so the app composition reflects
the modular-monolith boundaries.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.logging import configure_logging, get_logger
from app.middleware import RequestContextMiddleware

# Module routers (public api surfaces only).
from app.modules.auth.api import router as auth_router
from app.modules.tenants.api import router as tenants_router
from app.settings import AppEnv, get_settings

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    log.info("api.startup", env=settings.app_env, ai_provider=settings.ai_provider)
    yield
    log.info("api.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        json_output=settings.app_env != AppEnv.LOCAL,
    )

    app = FastAPI(
        title="Salesforce QA Requirement Intelligence Platform",
        version="0.0.1",
        lifespan=lifespan,
    )
    app.add_middleware(RequestContextMiddleware)

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readyz() -> dict[str, str]:
        # Sprint 0: liveness only. DB/Redis readiness checks land in Sprint 1.
        return {"status": "ready"}

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(tenants_router, prefix="/api/v1")

    return app


app = create_app()
