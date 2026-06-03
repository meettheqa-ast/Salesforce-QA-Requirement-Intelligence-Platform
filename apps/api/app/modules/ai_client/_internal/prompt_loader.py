"""Loads versioned prompts from the repo-root prompts/ directory.

Prompts are markdown files with a YAML front matter block. See prompts/README.md
for the convention. The loader binds each file to a stable (prompt_id, version)
key and caches parsed prompts in memory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.settings import get_settings

_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass(frozen=True, slots=True)
class Prompt:
    prompt_id: str
    version: int
    model_class: str
    expected_output: str
    body: str
    description: str


class PromptNotFound(Exception):
    pass


def _prompts_root() -> Path:
    settings = get_settings()
    # prompts_dir is relative to apps/api; resolve against this file's location.
    base = Path(__file__).resolve().parents[5]  # repo root
    candidate = (base / "prompts").resolve()
    if candidate.exists():
        return candidate
    # Fallback to the configured relative path.
    return (Path.cwd() / settings.prompts_dir).resolve()


def _parse(path: Path) -> Prompt:
    raw = path.read_text(encoding="utf-8")
    match = _FRONT_MATTER_RE.match(raw)
    if not match:
        raise ValueError(f"Prompt {path} is missing a YAML front matter block")
    meta = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()
    return Prompt(
        prompt_id=str(meta["prompt_id"]),
        version=int(meta["version"]),
        model_class=str(meta.get("model_class", "primary")),
        expected_output=str(meta.get("expected_output", "text")),
        body=body,
        description=str(meta.get("description", "")),
    )


@lru_cache
def _index() -> dict[tuple[str, int], Prompt]:
    root = _prompts_root()
    index: dict[tuple[str, int], Prompt] = {}
    for path in root.rglob("*.md"):
        if path.name.upper() == "README.MD":
            continue
        try:
            prompt = _parse(path)
        except (ValueError, KeyError):
            continue
        index[(prompt.prompt_id, prompt.version)] = prompt
    return index


def load_prompt(prompt_id: str, version: int) -> Prompt:
    try:
        return _index()[(prompt_id, version)]
    except KeyError as exc:
        raise PromptNotFound(
            f"No prompt for id={prompt_id!r} version={version}"
        ) from exc
