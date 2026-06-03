"""Token counting and cost estimation.

Prices are expressed in cents per million tokens and live in a single table so
updating them is a one-line change. These are placeholders and MUST be verified
against current provider pricing before any production billing relies on them.
"""

from __future__ import annotations

from .types import TokenUsage

# Placeholder prices (USD cents per 1M tokens). Verify before production use.
# Keyed by a coarse model family substring match.
_PRICE_TABLE_CENTS_PER_MTOK: dict[str, tuple[float, float]] = {
    # family substring : (input, output)
    "opus": (1500.0, 7500.0),
    "sonnet": (300.0, 1500.0),
    "haiku": (80.0, 400.0),
    "stub": (0.0, 0.0),
}


def _price_for(model: str) -> tuple[float, float]:
    lowered = model.lower()
    for family, price in _PRICE_TABLE_CENTS_PER_MTOK.items():
        if family in lowered:
            return price
    # Unknown model: assume primary-tier pricing to avoid under-billing.
    return _PRICE_TABLE_CENTS_PER_MTOK["opus"]


def estimate_cost_cents(model: str, usage: TokenUsage) -> float:
    in_price, out_price = _price_for(model)
    cost = (usage.input_tokens / 1_000_000) * in_price
    cost += (usage.output_tokens / 1_000_000) * out_price
    return round(cost, 6)


def count_tokens(text: str, model: str) -> int:
    """Best-effort token count. Uses tiktoken when available, else a heuristic."""
    try:
        import tiktoken

        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)
