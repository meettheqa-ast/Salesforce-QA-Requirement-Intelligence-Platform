"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from fastapi import Depends, HTTPException, Request

from app.context import set_request_context
from app.settings import get_settings

from .providers import AuthError, BaseAuthProvider, Principal, build_provider


@lru_cache
def _provider() -> BaseAuthProvider:
    return build_provider(get_settings())


def get_current_principal(request: Request) -> Principal:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = header[len("bearer ") :].strip()
    try:
        principal = _provider().verify(token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    # Promote the verified identity into the request context so DB sessions and
    # audit emission pick up the tenant and user automatically.
    ctx_request_id = request.headers.get("x-request-id")
    set_request_context(
        request_id=ctx_request_id or _new_request_id(),
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
    )
    return principal


def _new_request_id() -> str:
    from app.context import new_request_id

    return new_request_id()


def require_role(*allowed: str) -> Callable[[Principal], Principal]:
    def _checker(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return principal

    return _checker
