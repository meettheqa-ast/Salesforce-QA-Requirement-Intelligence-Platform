"""Shared types for the ai_client module."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ModelClass(StrEnum):
    CHEAP = "cheap"
    PRIMARY = "primary"


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    role: Role
    content: str


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


class CompletionResult(BaseModel):
    """The return value of every LLM call in the platform.

    `prompt_id` and `prompt_version` are stamped here so every downstream
    artifact records exactly which prompt produced it (reproducibility).
    """

    text: str
    model: str
    prompt_id: str
    prompt_version: int
    usage: TokenUsage
    cost_cents: float
    provider: str
    is_stub: bool


class BudgetExceeded(Exception):
    """Raised before contacting the LLM when a tenant is over budget."""


class LLMError(Exception):
    """Raised when the provider fails after retries."""
