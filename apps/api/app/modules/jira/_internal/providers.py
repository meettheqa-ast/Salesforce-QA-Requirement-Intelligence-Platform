"""Jira provider abstraction: a deterministic stub and a Cloud adapter.

StubJiraProvider returns a small canned corpus so the full ingestion pipeline
runs offline and tests are reproducible. JiraCloudProvider talks to the real
Jira Cloud REST API v3 with HTTP Basic auth (email + API token); it is wired
but only used when JIRA_PROVIDER=cloud and a connection's credentials are
present -- you supply those at runtime.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.logging import get_logger

from .types import JiraError, JiraIssue

log = get_logger(__name__)

# Canned corpus: covers a plain-text description, an ADF description, and an
# explicit Acceptance Criteria block so normalization is exercised end to end.
_STUB_ISSUES: list[JiraIssue] = [
    JiraIssue(
        key="DEMO-1",
        fields={
            "summary": "User can log in with email and password",
            "description": (
                "As a registered user I want to log in.\n"
                "Acceptance Criteria:\n"
                "- Valid credentials grant access\n"
                "- Invalid credentials show an error\n"
            ),
            "issuetype": {"name": "Story"},
            "status": {"name": "To Do"},
            "labels": ["auth", "mvp"],
        },
    ),
    JiraIssue(
        key="DEMO-2",
        fields={
            "summary": "Password reset via email",
            # ADF (Atlassian Document Format) description, as Cloud returns.
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "User requests a reset link."}
                        ],
                    }
                ],
            },
            "issuetype": {"name": "Story"},
            "status": {"name": "In Progress"},
            "labels": ["auth"],
        },
    ),
    JiraIssue(
        key="DEMO-3",
        fields={
            "summary": "Account lockout after repeated failures",
            "description": "Lock the account after 5 failed attempts.",
            "issuetype": {"name": "Bug"},
            "status": {"name": "Done"},
            "labels": [],
        },
    ),
]


class BaseJiraProvider(ABC):
    name: str

    @abstractmethod
    async def search_issues(self, jql: str, *, limit: int = 100) -> list[JiraIssue]: ...


class StubJiraProvider(BaseJiraProvider):
    name = "stub"

    async def search_issues(self, jql: str, *, limit: int = 100) -> list[JiraIssue]:
        log.info("jira.stub.search", jql=jql, count=len(_STUB_ISSUES))
        return list(_STUB_ISSUES[:limit])


class JiraCloudProvider(BaseJiraProvider):
    """Jira Cloud REST API v3 adapter (HTTP Basic: email + API token)."""

    name = "cloud"

    def __init__(
        self, *, base_url: str, email: str, api_token: str, timeout: float = 30.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = (email, api_token)
        self._timeout = timeout

    async def search_issues(self, jql: str, *, limit: int = 100) -> list[JiraIssue]:
        url = f"{self._base_url}/rest/api/3/search"
        params: dict[str, Any] = {
            "jql": jql,
            "maxResults": limit,
            "fields": "summary,description,issuetype,status,labels",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url, params=params, auth=self._auth)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as exc:
            raise JiraError(f"Jira Cloud search failed: {exc}") from exc
        return [
            JiraIssue(key=str(i.get("key")), fields=i.get("fields") or {})
            for i in data.get("issues", [])
        ]
