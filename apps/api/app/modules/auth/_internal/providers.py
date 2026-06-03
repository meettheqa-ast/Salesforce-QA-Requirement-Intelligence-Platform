"""Auth provider abstraction.

DevAuthProvider issues and verifies HS256 tokens with a shared dev secret so
local development needs no external IdP. OIDCProvider verifies RS256 tokens
against a remote JWKS (Auth0-style) and extracts claims.

Providers are responsible ONLY for cryptographic verification and claim
extraction. They return VerifiedClaims; resolving the final Principal
(including the DB-lookup fallback for tenant/role) happens in the request
dependency layer, where an async DB session is available.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx
from jose import JWTError, jwt

from app.logging import get_logger
from app.settings import AuthProvider, Settings

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str
    tenant_id: str
    email: str
    role: str


@dataclass(frozen=True, slots=True)
class VerifiedClaims:
    """Result of verifying a token's signature and standard claims.

    `tenant_id` and `role` are optional: an OIDC token may not carry them, in
    which case the dependency layer resolves them from the database.
    """

    subject: str
    email: str
    tenant_id: str | None
    role: str | None


class AuthError(Exception):
    """Raised when a token cannot be verified."""


class BaseAuthProvider(ABC):
    @abstractmethod
    def verify(self, token: str) -> VerifiedClaims: ...


class DevAuthProvider(BaseAuthProvider):
    """Local-development provider. NOT for any deployed environment."""

    _ALGO = "HS256"

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def issue(self, *, user_id: str, tenant_id: str, email: str, role: str) -> str:
        claims = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "role": role,
        }
        token: str = jwt.encode(claims, self._secret, algorithm=self._ALGO)
        return token

    def verify(self, token: str) -> VerifiedClaims:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[self._ALGO])
        except JWTError as exc:
            raise AuthError(str(exc)) from exc
        return VerifiedClaims(
            subject=claims["sub"],
            email=claims.get("email", ""),
            tenant_id=claims.get("tenant_id"),
            role=claims.get("role"),
        )


class _JWKSCache:
    """Caches a provider's JWKS for a TTL to avoid a network hop per request."""

    def __init__(self, jwks_url: str, ttl_seconds: int) -> None:
        self._url = jwks_url
        self._ttl = ttl_seconds
        self._keys: dict[str, dict[str, object]] | None = None
        self._fetched_at = 0.0

    def _fetch(self) -> dict[str, dict[str, object]]:
        try:
            resp = httpx.get(self._url, timeout=5.0)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise AuthError(f"Could not fetch JWKS from {self._url}: {exc}") from exc
        keys = {k["kid"]: k for k in resp.json().get("keys", []) if "kid" in k}
        if not keys:
            raise AuthError("JWKS response contained no usable keys")
        return keys

    def get(self, kid: str, *, force_refresh: bool = False) -> dict[str, object]:
        now = time.monotonic()
        expired = (now - self._fetched_at) > self._ttl
        if self._keys is None or expired or force_refresh:
            self._keys = self._fetch()
            self._fetched_at = now
        key = self._keys.get(kid)
        if key is None and not force_refresh:
            # Key rotation: a new kid may have appeared. Refresh once.
            return self.get(kid, force_refresh=True)
        if key is None:
            raise AuthError(f"No JWKS key matches token kid={kid!r}")
        return key


class OIDCProvider(BaseAuthProvider):
    """Verifies RS256 JWTs against a remote JWKS and extracts claims."""

    _ALGOS = ("RS256",)

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        jwks_cache_seconds: int,
        tenant_claim: str,
        role_claim: str,
    ) -> None:
        if not issuer:
            raise AuthError("AUTH_PROVIDER=oidc requires OIDC_ISSUER to be set.")
        self._issuer = issuer.rstrip("/")
        self._audience = audience
        self._tenant_claim = tenant_claim
        self._role_claim = role_claim
        resolved_jwks = jwks_url or f"{self._issuer}/.well-known/jwks.json"
        self._jwks = _JWKSCache(resolved_jwks, jwks_cache_seconds)

    def verify(self, token: str) -> VerifiedClaims:
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as exc:
            raise AuthError(f"Malformed token header: {exc}") from exc

        kid = header.get("kid")
        if not kid:
            raise AuthError("Token header missing 'kid'")
        key = self._jwks.get(kid)

        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=list(self._ALGOS),
                audience=self._audience or None,
                issuer=f"{self._issuer}/",
                options={"verify_aud": bool(self._audience)},
            )
        except JWTError as exc:
            raise AuthError(f"Token verification failed: {exc}") from exc

        subject = claims.get("sub")
        if not subject:
            raise AuthError("Token missing 'sub' claim")

        return VerifiedClaims(
            subject=str(subject),
            email=str(claims.get("email", "")),
            tenant_id=_optional_str(claims.get(self._tenant_claim)),
            role=_optional_str(claims.get(self._role_claim)),
        )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_provider(settings: Settings) -> BaseAuthProvider:
    if settings.auth_provider == AuthProvider.DEV:
        return DevAuthProvider(secret=settings.dev_auth_shared_secret)
    return OIDCProvider(
        issuer=settings.oidc_issuer,
        audience=settings.oidc_audience,
        jwks_url=settings.oidc_jwks_url,
        jwks_cache_seconds=settings.oidc_jwks_cache_seconds,
        tenant_claim=settings.oidc_tenant_claim,
        role_claim=settings.oidc_role_claim,
    )
