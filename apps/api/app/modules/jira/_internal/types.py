"""Jira domain types: raw issues and the canonical story they normalize to.

CanonicalStory is the stable, provider-independent shape the rest of the
platform consumes. Jira field variations (custom fields, ADF vs plain text,
hosted vs cloud) are absorbed in normalize.py so downstream modules never see
Jira-specific structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class JiraIssue:
    """A raw issue as returned by a provider (already JSON-decoded)."""

    key: str
    fields: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CanonicalStory:
    """Normalized requirement, stable across Jira variations."""

    source_key: str
    title: str
    body: str
    issue_type: str = ""
    status: str = ""
    labels: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class JiraError(Exception):
    """Raised when a Jira provider call fails."""
