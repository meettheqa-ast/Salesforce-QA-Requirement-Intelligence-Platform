"""Auth provider abstraction.

DevAuthProvider issues and verifies HS256 tokens with a shared dev secret so
local development needs no external IdP. OIDCProvider verifies RS256 tokens
against a remote JWKS; it is a thin stub in Sprint 0 and fully wired in Sprint 1.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from jose import JWTError, jwt

from app.settings import AuthProvider, Settings


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    tenant_id: str
    email: str
    role: str


class AuthError(Exception):
    """Raised when a token cannot be verified."""


class BaseAuthProvider(ABC):
    @abstractmethod
    def verify(self, token: str) -> Principal: ...


class DevAuthProvider(BaseAuthProvider):
    """Local-development provider. NOT for any deployed environment."""

    _ALGO = "HS256"

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def issue(
        self, *, user_id: str, tenant_id: str, email: str, role: str
    ) -> str:
        claims = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "role": role,
        }
        token: str = jwt.encode(claims, self._secret, algorithm=self._ALGO)
        return token

    def verify(self, token: str) -> Principal:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[self._ALGO])
        except JWTError as exc:
            raise AuthError(str(exc)) from exc
        return Principal(
            user_id=claims["sub"],
            tenant_id=claims["tenant_id"],
            email=claims.get("email", ""),
            role=claims.get("role", "viewer"),
        )


class OIDCProvider(BaseAuthProvider):
    """Verifies RS256 JWTs against a remote JWKS. Wired fully in Sprint 1."""

    def __init__(self, issuer: str, audience: str, jwks_url: str) -> None:
        self._issuer = issuer
        self._audience = audience
        self._jwks_url = jwks_url

    def verify(self, token: str) -> Principal:  # pragma: no cover - Sprint 1
        raise AuthError(
            "OIDC verification is not implemented until Sprint 1. "
            "Set AUTH_PROVIDER=dev for local development."
        )


def build_provider(settings: Settings) -> BaseAuthProvider:
    if settings.auth_provider == AuthProvider.DEV:
        return DevAuthProvider(secret=settings.dev_auth_shared_secret)
    return OIDCProvider(
        issuer=settings.oidc_issuer,
        audience=settings.oidc_audience,
        jwks_url=settings.oidc_jwks_url,
    )
