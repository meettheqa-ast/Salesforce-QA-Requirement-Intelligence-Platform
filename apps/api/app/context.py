"""Per-request context propagated via contextvars.

Holds the authenticated tenant and user for the lifetime of a request so that
database sessions can enforce RLS (`SET LOCAL app.current_tenant_id`) and audit
events can attribute actions, without threading these values through every
function signature.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_tenant_id: ContextVar[str | None] = ContextVar("tenant_id", default=None)
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str
    tenant_id: str | None
    user_id: str | None


def new_request_id() -> str:
    return str(uuid.uuid4())


def set_request_context(
    *, request_id: str, tenant_id: str | None, user_id: str | None
) -> None:
    _request_id.set(request_id)
    _tenant_id.set(tenant_id)
    _user_id.set(user_id)


def get_request_context() -> RequestContext:
    return RequestContext(
        request_id=_request_id.get() or new_request_id(),
        tenant_id=_tenant_id.get(),
        user_id=_user_id.get(),
    )


def current_tenant_id() -> str | None:
    return _tenant_id.get()


def require_tenant_id() -> str:
    tenant = _tenant_id.get()
    if tenant is None:
        raise RuntimeError(
            "No tenant in request context. A tenant-scoped operation was "
            "attempted outside an authenticated request."
        )
    return tenant


def current_user_id() -> str | None:
    return _user_id.get()
