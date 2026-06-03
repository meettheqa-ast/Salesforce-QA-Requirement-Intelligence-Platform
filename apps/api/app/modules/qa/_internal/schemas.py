"""Request/response DTOs for the QA module (Sprint 1 minimal surface)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    # Bounds the answer size and, with it, the worst-case output cost.
    max_tokens: int = Field(default=1024, ge=64, le=4096)


class AskResponse(BaseModel):
    answer: str
    model: str
    prompt_id: str
    prompt_version: int
    input_tokens: int
    output_tokens: int
    cost_cents: float
    provider: str
    is_stub: bool
