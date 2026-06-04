"""Envelope encryption for secrets at rest.

This is infrastructure (like db.py), not a domain module, so it lives at the app
level and is not subject to the module-boundary import rules. The ONLY domain
module permitted to call encrypt/decrypt is `connections` (see docs/AGENTS.md):
it is the single place tenant credentials are sealed and opened.

Envelope scheme (provider-agnostic):
  1. Generate a random 256-bit data encryption key (DEK) per secret.
  2. Encrypt the plaintext with the DEK using AES-256-GCM (authenticated).
  3. Encrypt (wrap) the DEK with the key-encryption key (KEK) from the KMS.
  4. Store {wrapped_dek, nonce, ciphertext}. The plaintext DEK is never stored.

Local provider: the KEK is derived from KMS_LOCAL_MASTER_KEY via SHA-256, so any
configured string yields a valid 32-byte key for development. AWS/GCP KMS
providers wrap/unwrap the DEK with a managed CMK and are stubbed until needed.
Production MUST use a managed KMS; the local provider is for dev/test only.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from abc import ABC, abstractmethod

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.settings import KMSProvider, Settings, get_settings

_NONCE_BYTES = 12  # AES-GCM standard nonce size.
_DEK_BYTES = 32  # AES-256.
_ENVELOPE_VERSION = 1


class CryptoError(Exception):
    """Raised when sealing or opening a secret fails."""


class BaseKEK(ABC):
    """A key-encryption key: wraps/unwraps data keys."""

    provider: str

    @abstractmethod
    def wrap(self, dek: bytes) -> bytes: ...

    @abstractmethod
    def unwrap(self, wrapped: bytes) -> bytes: ...


class LocalKEK(BaseKEK):
    """Dev-only KEK derived from a configured master string. NOT for production."""

    provider = "local"

    def __init__(self, master_key_material: str) -> None:
        # Derive a stable 32-byte key from whatever string is configured.
        self._kek = hashlib.sha256(master_key_material.encode("utf-8")).digest()

    def wrap(self, dek: bytes) -> bytes:
        nonce = os.urandom(_NONCE_BYTES)
        ct = AESGCM(self._kek).encrypt(nonce, dek, None)
        return nonce + ct

    def unwrap(self, wrapped: bytes) -> bytes:
        nonce, ct = wrapped[:_NONCE_BYTES], wrapped[_NONCE_BYTES:]
        try:
            return AESGCM(self._kek).decrypt(nonce, ct, None)
        except Exception as exc:  # invalid key/tag
            raise CryptoError("Failed to unwrap data key") from exc


def _build_kek(settings: Settings) -> BaseKEK:
    if settings.kms_provider == KMSProvider.LOCAL:
        return LocalKEK(settings.kms_local_master_key)
    # AWS/GCP KMS wrap the DEK with a managed CMK. Wired when those environments
    # exist; until then, fail loudly rather than silently using a weaker path.
    raise CryptoError(
        f"KMS provider {settings.kms_provider!r} is not implemented yet. "
        "Use KMS_PROVIDER=local for development."
    )


def _kek() -> BaseKEK:
    return _build_kek(get_settings())


def seal(plaintext: str) -> str:
    """Encrypt a secret, returning a self-describing base64 envelope string."""
    kek = _kek()
    dek = os.urandom(_DEK_BYTES)
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = AESGCM(dek).encrypt(nonce, plaintext.encode("utf-8"), None)
    wrapped = kek.wrap(dek)
    envelope = {
        "v": _ENVELOPE_VERSION,
        "p": kek.provider,
        "wdek": base64.b64encode(wrapped).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ciphertext).decode("ascii"),
    }
    return base64.b64encode(json.dumps(envelope).encode("utf-8")).decode("ascii")


def open_secret(envelope_str: str) -> str:
    """Decrypt an envelope produced by `seal`. Never log the return value."""
    kek = _kek()
    try:
        envelope = json.loads(base64.b64decode(envelope_str))
        wrapped = base64.b64decode(envelope["wdek"])
        nonce = base64.b64decode(envelope["nonce"])
        ciphertext = base64.b64decode(envelope["ct"])
    except Exception as exc:
        raise CryptoError("Malformed secret envelope") from exc

    dek = kek.unwrap(wrapped)
    try:
        return AESGCM(dek).decrypt(nonce, ciphertext, None).decode("utf-8")
    except Exception as exc:
        raise CryptoError("Failed to decrypt secret payload") from exc
