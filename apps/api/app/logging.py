"""Structured logging with a secret denylist.

Per docs/AGENTS.md, secret-shaped strings must never reach the logs. This
module configures structlog and installs a processor that redacts known
secret patterns defensively, in addition to the discipline of never passing
secrets to log calls in the first place.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import structlog

# Patterns that look like secrets. Defensive backstop, not the primary control.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"ATATT[A-Za-z0-9_\-=]{10,}"),  # Atlassian API tokens
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style keys
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),  # Anthropic keys
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{20,}"),  # bearer tokens
)

_REDACTED = "[REDACTED]"


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        redacted = value
        for pattern in _SECRET_PATTERNS:
            redacted = pattern.sub(_REDACTED, redacted)
        return redacted
    return value


def _redact_processor(
    _logger: Any, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    for key, val in list(event_dict.items()):
        event_dict[key] = _redact_value(val)
    return event_dict


def configure_logging(level: str = "INFO", *, json_output: bool = True) -> None:
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=log_level)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact_processor,
    ]
    processors.append(
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
