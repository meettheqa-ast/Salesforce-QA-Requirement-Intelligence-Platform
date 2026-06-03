"""OIDCProvider verification against a locally-generated RSA key + mocked JWKS.

No network and no DB: we build a JWKS in-memory, monkeypatch the cache's fetch,
and assert signature/issuer/audience/expiry behavior and claim extraction.
"""

from __future__ import annotations

import time

import pytest
from app.modules.auth._internal.providers import (
    AuthError,
    OIDCProvider,
    _JWKSCache,
)
from jose import jwt

ISSUER = "https://example-tenant.us.auth0.com"
AUDIENCE = "https://sfqa.api"
TENANT_CLAIM = "https://sfqa.app/tenant_id"
ROLE_CLAIM = "https://sfqa.app/role"
KID = "test-key-1"


@pytest.fixture(scope="module")
def rsa_keys() -> dict[str, str]:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return {"private": private_pem, "public": public_pem}


@pytest.fixture
def provider(rsa_keys: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> OIDCProvider:
    # The JWK is a PEM-form public key; python-jose accepts a PEM string as the
    # verification key, so we stash the PEM under the kid and bypass network.
    jwk_entry = {"kid": KID, "_pem": rsa_keys["public"]}

    def fake_get(self: _JWKSCache, kid: str, *, force_refresh: bool = False) -> dict:
        if kid != KID:
            raise AuthError(f"No JWKS key matches token kid={kid!r}")
        return jwk_entry

    monkeypatch.setattr(_JWKSCache, "get", fake_get)

    prov = OIDCProvider(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url="https://unused.example/jwks.json",
        jwks_cache_seconds=3600,
        tenant_claim=TENANT_CLAIM,
        role_claim=ROLE_CLAIM,
    )
    # python-jose verifies against the value we return from the cache; it expects
    # a key it can interpret. We return the PEM string directly.
    monkeypatch.setattr(
        prov._jwks, "get", lambda kid, force_refresh=False: rsa_keys["public"]
    )
    return prov


def _make_token(
    private_pem: str,
    *,
    claims: dict | None = None,
    exp_delta: int = 3600,
    aud: str = AUDIENCE,
    iss: str = f"{ISSUER}/",
) -> str:
    now = int(time.time())
    payload = {
        "sub": "auth0|abc123",
        "email": "user@example.com",
        "iss": iss,
        "aud": aud,
        "iat": now,
        "exp": now + exp_delta,
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": KID})


def test_valid_token_with_custom_claims(
    provider: OIDCProvider, rsa_keys: dict[str, str]
) -> None:
    token = _make_token(
        rsa_keys["private"],
        claims={TENANT_CLAIM: "tenant-xyz", ROLE_CLAIM: "qa_lead"},
    )
    verified = provider.verify(token)
    assert verified.subject == "auth0|abc123"
    assert verified.email == "user@example.com"
    assert verified.tenant_id == "tenant-xyz"
    assert verified.role == "qa_lead"


def test_valid_token_without_custom_claims_leaves_them_none(
    provider: OIDCProvider, rsa_keys: dict[str, str]
) -> None:
    token = _make_token(rsa_keys["private"])
    verified = provider.verify(token)
    assert verified.subject == "auth0|abc123"
    assert verified.tenant_id is None
    assert verified.role is None


def test_expired_token_rejected(
    provider: OIDCProvider, rsa_keys: dict[str, str]
) -> None:
    token = _make_token(rsa_keys["private"], exp_delta=-10)
    with pytest.raises(AuthError):
        provider.verify(token)


def test_wrong_audience_rejected(
    provider: OIDCProvider, rsa_keys: dict[str, str]
) -> None:
    token = _make_token(rsa_keys["private"], aud="https://attacker.example")
    with pytest.raises(AuthError):
        provider.verify(token)


def test_wrong_issuer_rejected(
    provider: OIDCProvider, rsa_keys: dict[str, str]
) -> None:
    token = _make_token(rsa_keys["private"], iss="https://evil.example/")
    with pytest.raises(AuthError):
        provider.verify(token)


def test_tampered_signature_rejected(
    provider: OIDCProvider, rsa_keys: dict[str, str]
) -> None:
    token = _make_token(rsa_keys["private"])
    # Flip a character in the signature segment.
    head, payload, sig = token.split(".")
    bad_sig = ("A" if sig[0] != "A" else "B") + sig[1:]
    with pytest.raises(AuthError):
        provider.verify(f"{head}.{payload}.{bad_sig}")
