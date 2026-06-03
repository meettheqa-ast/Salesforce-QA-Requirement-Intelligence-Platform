"""QA business logic (Sprint 1 minimal surface).

This runs the user's question through the versioned `qa.answer` prompt via the
ai_client chokepoint. Retrieval (RAG) is NOT wired yet -- that is Sprint 4 -- so
the prompt is told explicitly that no retrieved context is available. The point
of this endpoint in Sprint 1 is to exercise the full guarded LLM path end to
end: budget gate -> provider -> usage metering -> audit.
"""

from __future__ import annotations

from app.modules.ai_client.api import complete

from .schemas import AskRequest, AskResponse

_PROMPT_ID = "qa.answer"
_PROMPT_VERSION = 1

_NO_CONTEXT_NOTICE = (
    "<retrieved_content>\n"
    "(No retrieval is wired yet. Treat this as an empty context. If you cannot "
    "answer from general knowledge without project-specific sources, set "
    '"answered" to false and say what would be needed.)\n'
    "</retrieved_content>\n\n"
    "Question: "
)


async def ask(req: AskRequest) -> AskResponse:
    user_content = f"{_NO_CONTEXT_NOTICE}{req.question}"
    result = await complete(
        prompt_id=_PROMPT_ID,
        prompt_version=_PROMPT_VERSION,
        user_content=user_content,
        max_tokens=req.max_tokens,
    )
    return AskResponse(
        answer=result.text,
        model=result.model,
        prompt_id=result.prompt_id,
        prompt_version=result.prompt_version,
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
        cost_cents=result.cost_cents,
        provider=result.provider,
        is_stub=result.is_stub,
    )
