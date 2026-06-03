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

__all__: list[str] = []
