"""LLM provider abstraction with a deterministic stub and an Anthropic adapter.

The stub returns canned, deterministic responses so the platform runs offline
and tests are reproducible. The Anthropic adapter is wired but only used when
AI_PROVIDER=anthropic and a key is present.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

from app.logging import get_logger
from app.settings import AIProvider, Settings

from .types import LLMError, Message, TokenUsage

log = get_logger(__name__)


class BaseLLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete(
        self, *, model: str, messages: list[Message], max_tokens: int
    ) -> tuple[str, TokenUsage]: ...


class StubLLMProvider(BaseLLMProvider):
    """Deterministic provider. Echoes a hash-stable canned response.

    The response is derived from the input so tests can assert determinism,
    and is shaped as minimal valid JSON when the last message hints JSON.
    """

    name = "stub"

    async def complete(
        self, *, model: str, messages: list[Message], max_tokens: int
    ) -> tuple[str, TokenUsage]:
        joined = "\n".join(m.content for m in messages)
        digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:12]
        wants_json = "json" in joined.lower()
        if wants_json:
            text = (
                f'{{"stub": true, "digest": "{digest}", '
                '"note": "deterministic stub response"}'
            )
        else:
            text = f"[stub:{digest}] deterministic response for model={model}"
        usage = TokenUsage(
            input_tokens=_rough_tokens(joined),
            output_tokens=_rough_tokens(text),
        )
        return text, usage


class AnthropicLLMProvider(BaseLLMProvider):
    """Anthropic API adapter. Imported lazily so the SDK is optional in dev."""

    name = "anthropic"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def complete(
        self, *, model: str, messages: list[Message], max_tokens: int
    ) -> tuple[str, TokenUsage]:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:  # pragma: no cover
            raise LLMError(
                "anthropic SDK not installed. Add it to dependencies or use "
                "AI_PROVIDER=stub."
            ) from exc

        system = "\n".join(m.content for m in messages if m.role == "system")
        turns = [
            {"role": m.role.value, "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        client = AsyncAnthropic(api_key=self._api_key)
        try:
            resp = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system or None,
                messages=turns,
            )
        except Exception as exc:  # pragma: no cover - network
            raise LLMError(f"Anthropic call failed: {exc}") from exc

        text = "".join(
            block.text for block in resp.content if block.type == "text"
        )
        usage = TokenUsage(
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )
        return text, usage


def _rough_tokens(text: str) -> int:
    # Cheap heuristic for the stub; real counting uses tiktoken in cost.py.
    return max(1, len(text) // 4)


def build_provider(settings: Settings) -> BaseLLMProvider:
    if settings.ai_provider == AIProvider.ANTHROPIC:
        if not settings.anthropic_api_key:
            raise LLMError(
                "AI_PROVIDER=anthropic but ANTHROPIC_API_KEY is empty."
            )
        return AnthropicLLMProvider(api_key=settings.anthropic_api_key)
    return StubLLMProvider()
