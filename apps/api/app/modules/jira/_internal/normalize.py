"""Normalize raw Jira issues into CanonicalStory.

Handles the two description shapes Jira returns: plain strings (server / some
APIs) and Atlassian Document Format (ADF, a nested JSON doc on Cloud). Unknown
shapes degrade to an empty body rather than raising, so one malformed issue
never fails a whole sync.
"""

from __future__ import annotations

import re
from typing import Any

from .types import CanonicalStory, JiraIssue

_AC_HEADING = re.compile(
    r"acceptance criteria[:\s]*", re.IGNORECASE
)
_BULLET = re.compile(r"^\s*[-*\u2022]\s+(.*)$")


def _adf_to_text(node: Any) -> str:
    """Flatten an ADF node tree into plain text."""
    if not isinstance(node, dict):
        return ""
    parts: list[str] = []
    if node.get("type") == "text" and isinstance(node.get("text"), str):
        parts.append(node["text"])
    for child in node.get("content", []) or []:
        parts.append(_adf_to_text(child))
    # Block-level nodes get a newline so paragraphs/list items separate.
    if node.get("type") in {"paragraph", "listItem", "heading"}:
        parts.append("\n")
    return "".join(parts)


def _description_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):  # ADF
        return _adf_to_text(value).strip()
    return ""


def _extract_acceptance_criteria(body: str) -> list[str]:
    """Best-effort: collect bullet lines under an 'Acceptance Criteria' heading."""
    lines = body.splitlines()
    criteria: list[str] = []
    capturing = False
    for line in lines:
        if _AC_HEADING.search(line):
            capturing = True
            continue
        if capturing:
            m = _BULLET.match(line)
            if m:
                criteria.append(m.group(1).strip())
            elif line.strip() == "":
                continue
            else:
                # A non-bullet, non-empty line ends the AC block.
                break
    return criteria


def normalize_issue(issue: JiraIssue) -> CanonicalStory:
    fields = issue.fields or {}
    summary = str(fields.get("summary") or "").strip()
    body = _description_to_text(fields.get("description"))

    issue_type = ""
    if isinstance(fields.get("issuetype"), dict):
        issue_type = str(fields["issuetype"].get("name") or "")
    status = ""
    if isinstance(fields.get("status"), dict):
        status = str(fields["status"].get("name") or "")
    labels = [str(label) for label in (fields.get("labels") or [])]

    return CanonicalStory(
        source_key=issue.key,
        title=summary,
        body=body,
        issue_type=issue_type,
        status=status,
        labels=labels,
        acceptance_criteria=_extract_acceptance_criteria(body),
        metadata={"issue_type": issue_type, "status": status, "labels": labels},
    )
