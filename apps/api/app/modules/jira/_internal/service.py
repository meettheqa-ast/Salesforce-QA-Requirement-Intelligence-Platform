"""Jira ingestion orchestration.

build_provider selects stub vs cloud from settings. For cloud, credentials come
from the connections module's audited decrypt path -- jira never reads sealed
secrets itself. sync_repository pulls issues, normalizes them, and hands the
canonical stories to the repositories module as an immutable version.
"""

from __future__ import annotations

import uuid

from app.logging import get_logger
from app.modules.repositories.api import NormalizedDocument, ingest_version
from app.settings import JiraProvider, Settings, get_settings

from .normalize import normalize_issue
from .providers import BaseJiraProvider, JiraCloudProvider, StubJiraProvider
from .types import CanonicalStory, JiraError

log = get_logger(__name__)

# Pulls every issue in a project; the stub ignores JQL. Kept simple for MVP.
_DEFAULT_JQL = "ORDER BY created ASC"


async def _build_provider(connection_id: uuid.UUID | None) -> BaseJiraProvider:
    settings: Settings = get_settings()
    if settings.jira_provider == JiraProvider.STUB:
        return StubJiraProvider()

    if connection_id is None:
        raise JiraError(
            "JIRA_PROVIDER=cloud requires a connection_id with credentials."
        )
    # Audited decrypt via the only module allowed to open secrets.
    from app.modules.connections.api import get_credentials_for_use

    creds = await get_credentials_for_use(connection_id, purpose="jira_sync")
    return JiraCloudProvider(
        base_url=creds.base_url,
        email=creds.principal,
        api_token=creds.secret,
    )


async def fetch_stories(
    connection_id: uuid.UUID | None, *, jql: str | None = None, limit: int = 100
) -> list[CanonicalStory]:
    provider = await _build_provider(connection_id)
    issues = await provider.search_issues(jql or _DEFAULT_JQL, limit=limit)
    return [normalize_issue(issue) for issue in issues]


async def sync_repository(
    *,
    repository_id: uuid.UUID,
    connection_id: uuid.UUID | None,
    idempotency_key: str,
    jql: str | None = None,
) -> uuid.UUID:
    """Pull issues, normalize, and store them as a new repository version.

    Returns the version id. Idempotent via idempotency_key (see
    repositories.ingest_version). Designed to run inside the arq sync job.
    """
    stories = await fetch_stories(connection_id, jql=jql)
    documents = [
        NormalizedDocument(
            source_key=s.source_key,
            title=s.title,
            body=s.body,
            metadata=s.metadata,
        )
        for s in stories
    ]
    version = await ingest_version(
        repository_id=repository_id,
        documents=documents,
        idempotency_key=idempotency_key,
    )
    log.info(
        "jira.sync.complete",
        repository_id=str(repository_id),
        version_id=str(version.id),
        document_count=version.document_count,
    )
    return version.id
