"""The stub LLM provider must be deterministic and cost-free."""

from __future__ import annotations

import pytest
from app.modules.ai_client._internal.cost import estimate_cost_cents
from app.modules.ai_client._internal.providers import StubLLMProvider
from app.modules.ai_client._internal.types import Message, Role, TokenUsage


@pytest.mark.asyncio
async def test_stub_is_deterministic() -> None:
    provider = StubLLMProvider()
    messages = [Message(role=Role.USER, content="analyze this story")]
    text_a, usage_a = await provider.complete(
        model="stub", messages=messages, max_tokens=128
    )
    text_b, usage_b = await provider.complete(
        model="stub", messages=messages, max_tokens=128
    )
    assert text_a == text_b
    assert usage_a.total == usage_b.total


@pytest.mark.asyncio
async def test_stub_emits_json_when_hinted() -> None:
    provider = StubLLMProvider()
    messages = [Message(role=Role.USER, content="return JSON please")]
    text, _ = await provider.complete(model="stub", messages=messages, max_tokens=64)
    assert text.strip().startswith("{")


def test_stub_model_is_free() -> None:
    usage = TokenUsage(input_tokens=1000, output_tokens=1000)
    assert estimate_cost_cents("stub", usage) == 0.0


def test_opus_costs_more_than_haiku() -> None:
    usage = TokenUsage(input_tokens=1000, output_tokens=1000)
    assert estimate_cost_cents("claude-opus-4-5", usage) > estimate_cost_cents(
        "claude-haiku-4-5", usage
    )
