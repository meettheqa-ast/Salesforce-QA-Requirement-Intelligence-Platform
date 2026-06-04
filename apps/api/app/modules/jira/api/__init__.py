"""Public API of the jira module (Sprint 2).

Planned surface:
  - search_issues(jql, ...) / get_issue(key) / list_comments(key)
  - create_issue(...) for publishing
  - sync_repository(repository_id) -> job_id (long-running)
  - normalization to a canonical story schema, stable across Jira variations

StubJiraProvider returns a small canned corpus when JIRA_PROVIDER=stub.
Implemented in Sprint 2.
"""

from __future__ import annotations

from app.modules.jira._internal.normalize import normalize_issue
from app.modules.jira._internal.service import (
    fetch_stories,
    sync_repository,
)
from app.modules.jira._internal.types import (
    CanonicalStory,
    JiraError,
    JiraIssue,
)

__all__ = [
    "CanonicalStory",
    "JiraError",
    "JiraIssue",
    "fetch_stories",
    "normalize_issue",
    "sync_repository",
]
