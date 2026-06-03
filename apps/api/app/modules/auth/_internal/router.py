"""Auth routes.

In dev mode, exposes a token-mint endpoint so local clients (and tests) can
obtain a bearer token without an external IdP. Disabled outside dev provider.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.settings import AuthProvider, get_settings

from .dependencies import get_current_principal
from .providers import DevAuthProvider, Principal

router = APIRouter(prefix="/auth", tags=["auth"])


class DevTokenRequest(BaseModel):
    user_id: str
    tenant_id: str
    email: str = "dev@example.com"
    role: str = "tenant_admin"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/dev-token", response_model=TokenResponse)
async def mint_dev_token(req: DevTokenRequest) -> TokenResponse:
    settings = get_settings()
    if settings.auth_provider != AuthProvider.DEV:
        raise HTTPException(status_code=404, detail="Not available")
    provider = DevAuthProvider(secret=settings.dev_auth_shared_secret)
    token = provider.issue(
        user_id=req.user_id,
        tenant_id=req.tenant_id,
        email=req.email,
        role=req.role,
    )
    return TokenResponse(access_token=token)


class WhoAmI(BaseModel):
    user_id: str
    tenant_id: str
    email: str
    role: str


@router.get("/me", response_model=WhoAmI)
async def whoami(principal: Principal = Depends(get_current_principal)) -> WhoAmI:
    return WhoAmI(
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        email=principal.email,
        role=principal.role,
    )
