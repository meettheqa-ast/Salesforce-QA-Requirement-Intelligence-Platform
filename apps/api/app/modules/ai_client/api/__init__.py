"""Public API of the ai_client module.

`complete` is the ONLY sanctioned way to call an LLM in this codebase.
"""

from __future__ import annotations

from app.modules.ai_client._internal.cost import count_tokens
from app.modules.ai_client._internal.service import complete
from app.modules.ai_client._internal.types import (
    BudgetExceeded,
    CompletionResult,
    LLMError,
    ModelClass,
    TokenUsage,
)

__all__ = [
    "BudgetExceeded",
    "CompletionResult",
    "LLMError",
    "ModelClass",
    "TokenUsage",
    "complete",
    "count_tokens",
]
