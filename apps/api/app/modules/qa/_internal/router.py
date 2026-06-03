"""QA routes (Sprint 1 minimal surface)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.modules.ai_client.api import BudgetExceeded, LLMError
from app.modules.auth.api import Principal, require_role

from .schemas import AskRequest, AskResponse
from .service import ask as ask_service

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/ask", response_model=AskResponse)
async def ask(
    req: AskRequest,
    _principal: Principal = Depends(
        require_role("tenant_admin", "qa_lead", "qa_engineer")
    ),
) -> AskResponse:
    try:
        return await ask_service(req)
    except BudgetExceeded as exc:
        # 402 Payment Required: the tenant's monthly budget cap would be exceeded.
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
