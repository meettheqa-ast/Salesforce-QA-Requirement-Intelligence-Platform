"""Envelope encryption: round-trip, tamper detection, and no-plaintext-leak.

No DB. Exercises app.crypto directly with the local KEK.
"""

from __future__ import annotations

import base64
import json

import pytest
from app.crypto import CryptoError, open_secret, seal


def test_seal_open_round_trip() -> None:
    secret = "super-secret-jira-token-123"
    envelope = seal(secret)
    assert secret not in envelope  # ciphertext must not contain plaintext
    assert open_secret(envelope) == secret


def test_each_seal_is_unique() -> None:
    # Random DEK + nonce per call means identical plaintext yields different
    # envelopes (no deterministic ciphertext that could leak equality).
    a = seal("same")
    b = seal("same")
    assert a != b
    assert open_secret(a) == open_secret(b) == "same"


def test_tampered_ciphertext_is_rejected() -> None:
    envelope = seal("token")
    decoded = json.loads(base64.b64decode(envelope))
    ct = bytearray(base64.b64decode(decoded["ct"]))
    ct[0] ^= 0xFF  # flip a bit
    decoded["ct"] = base64.b64encode(bytes(ct)).decode("ascii")
    tampered = base64.b64encode(json.dumps(decoded).encode()).decode("ascii")
    with pytest.raises(CryptoError):
        open_secret(tampered)


def test_malformed_envelope_is_rejected() -> None:
    with pytest.raises(CryptoError):
        open_secret("not-a-valid-envelope")
