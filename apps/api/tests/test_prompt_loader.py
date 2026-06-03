"""The prompt loader must parse front matter and bind (id, version)."""

from __future__ import annotations

import pytest
from app.modules.ai_client._internal.prompt_loader import (
    PromptNotFound,
    load_prompt,
)


def test_loads_known_prompt() -> None:
    prompt = load_prompt("analysis.triage", 1)
    assert prompt.prompt_id == "analysis.triage"
    assert prompt.version == 1
    assert prompt.model_class == "cheap"
    assert prompt.expected_output == "json"
    assert "triage" in prompt.body.lower()


def test_missing_prompt_raises() -> None:
    with pytest.raises(PromptNotFound):
        load_prompt("does.not.exist", 99)
