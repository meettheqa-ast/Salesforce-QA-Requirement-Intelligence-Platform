"""The structured logger must redact secret-shaped strings."""

from __future__ import annotations

from app.logging import _redact_processor


def test_redacts_anthropic_key() -> None:
    event = {"msg": "key is sk-ant-abcdefghijklmnopqrstuvwxyz0123456789"}
    out = _redact_processor(None, "info", dict(event))
    assert "sk-ant-" not in out["msg"]
    assert "[REDACTED]" in out["msg"]


def test_redacts_bearer_token() -> None:
    event = {"auth": "Bearer abcdefghijklmnopqrstuvwxyz0123456789"}
    out = _redact_processor(None, "info", dict(event))
    assert "[REDACTED]" in out["auth"]


def test_leaves_clean_strings_untouched() -> None:
    event = {"msg": "a normal log line about repositories"}
    out = _redact_processor(None, "info", dict(event))
    assert out["msg"] == "a normal log line about repositories"
