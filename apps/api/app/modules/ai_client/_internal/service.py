"""The single chokepoint for all LLM calls in the platform.

Responsibilities, in order:
  1. Load the versioned prompt (prompt_id, version).
  2. Build the message list (system prompt + user content).
  3. Estimate cost and check the tenant budget BEFORE contacting the provider.
  4. Call the provider with retries.
  5. Compute actual cost, record usage, emit an audit event.
  6. Return a CompletionResult stamped with model + prompt version.

No other module may call an LLM provider directly. See docs/AGENTS.md.
"""

from __future__ import annotations

from functools import lru_cache

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.logging import get_logger
from app.modules.audit.api import emit
from app.modules.metering.api import check_budget, record_usage
from app.settings import Settings, get_settings

from .cost import count_tokens, estimate_cost_cents
from .prompt_loader import load_prompt
from .providers import BaseLLMProvider, build_provider
from .types import (
    BudgetExceeded,
    CompletionResult,
    LLMError,
    Message,
    ModelClass,
    Role,
    TokenUsage,
)

log = get_logger(__name__)


@lru_cache
def _provider() -> BaseLLMProvider:
    return build_provider(get_settings())


def _model_for(model_class: ModelClass, settings: Settings) -> str:
    if model_class == ModelClass.CHEAP:
        return settings.anthropic_model_cheap
    return settings.anthropic_model_primary


@retry(
    retry=retry_if_exception_type(LLMError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=8),
    reraise=True,
)
async def _call_provider(
    provider: BaseLLMProvider, *, model: str, messages: list[Message], max_tokens: int
) -> tuple[str, TokenUsage]:
    return await provider.complete(
        model=model, messages=messages, max_tokens=max_tokens
    )


async def complete(
    *,
    prompt_id: str,
    prompt_version: int,
    user_content: str,
    max_tokens: int = 2048,
) -> CompletionResult:
    settings = get_settings()
    prompt = load_prompt(prompt_id, prompt_version)
    model = _model_for(ModelClass(prompt.model_class), settings)

    messages = [
        Message(role=Role.SYSTEM, content=prompt.body),
        Message(role=Role.USER, content=user_content),
    ]

    # Pre-call budget gate using an input-token estimate plus a headroom guess
    # for output. We estimate conservatively so we never blow the cap.
    est_input = count_tokens(prompt.body + user_content, model)
    est_usage = TokenUsage(input_tokens=est_input, output_tokens=max_tokens)
    est_cost = estimate_cost_cents(model, est_usage)
    if not await check_budget(est_cost):
        await emit(
            "ai.budget_exceeded",
            resource_type="prompt",
            resource_id=prompt_id,
            payload={"estimated_cost_cents": est_cost},
        )
        raise BudgetExceeded(
            f"Tenant monthly budget would be exceeded by this call "
            f"(estimated {est_cost} cents)."
        )

    provider = _provider()
    text, usage = await _call_provider(
        provider, model=model, messages=messages, max_tokens=max_tokens
    )
    cost = estimate_cost_cents(model, usage)

    await record_usage(
        model=model,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cost_cents=cost,
    )
    await emit(
        "ai.completion",
        resource_type="prompt",
        resource_id=prompt_id,
        payload={
            "prompt_version": prompt_version,
            "model": model,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_cents": cost,
            "provider": provider.name,
        },
    )

    return CompletionResult(
        text=text,
        model=model,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        usage=usage,
        cost_cents=cost,
        provider=provider.name,
        is_stub=provider.name == "stub",
    )
