"""FastAPI dependencies for authentication and authorization.

The dependency is async because resolving a Principal may require a DB lookup
(the fallback when an OIDC token carries no tenant/role custom claims). The
provider performs only cryptographic verification + claim extraction; tenant and
role resolution -- the data behind the tenant-isolation boundary -- is decided
here, deterministically.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import lru_cache

from fastapi import Depends, HTTPException, Request

from app.context import new_request_id, set_request_context
from app.modules.tenants.api import resolve_identity
from app.settings import get_settings

from .providers import AuthError, BaseAuthProvider, Principal, VerifiedClaims, build_provider


@lru_cache
def _provider() -> BaseAuthProvider:
    return build_provider(get_settings())


async def _resolve_principal(claims: VerifiedClaims) -> Principal:
    # Claims-first: if the IdP token carries tenant + role, trust them.
    if claims.tenant_id and claims.role:
        return Principal(
            user_id=claims.subject,
            tenant_id=claims.tenant_id,
            email=claims.email,
            role=claims.role,
        )

    # Fallback: resolve membership from the database by subject/email.
    resolved = await resolve_identity(
        sso_subject=claims.subject, email=claims.email
    )
    if resolved is None:
        raise HTTPException(
            status_code=403,
            detail=(
                "Authenticated, but no tenant membership found for this user. "
                "The token carried no tenant claim and no matching membership "
                "exists."
            ),
        )
    # A token-provided tenant claim (if any) must agree with the DB to avoid a
    # user asserting a tenant they don't belong to. Without a claim, use the DB.
    tenant_id = str(resolved.tenant_id)
    if claims.tenant_id and claims.tenant_id != tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Token tenant claim does not match the user's membership.",
        )
    return Principal(
        user_id=str(resolved.user_id),
        tenant_id=tenant_id,
        email=claims.email,
        role=claims.role or resolved.role,
    )


async def get_current_principal(request: Request) -> Principal:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = header[len("bearer ") :].strip()
    try:
        claims = _provider().verify(token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    principal = await _resolve_principal(claims)

    # Promote the verified identity into the request context so DB sessions and
    # audit emission pick up the tenant and user automatically.
    ctx_request_id = request.headers.get("x-request-id")
    set_request_context(
        request_id=ctx_request_id or new_request_id(),
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
    )
    return principal


def require_role(
    *allowed: str,
) -> Callable[[Principal], Awaitable[Principal]]:
    async def _checker(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return principal

    return _checker
