"""Public API of the repositories module (Sprint 2).

Planned surface:
  - create_repository / get_repository / list_repositories
  - archive / delete (soft) / hard-delete workflow
  - RepositoryVersion + RepositoryDocument lifecycle
  - get_documents(version_id, ...)

Owns: repositories, repository_versions, repository_documents,
repository_document_chunks. All tenant-scoped with RLS. Implemented in Sprint 2.
"""

from __future__ import annotations

from app.modules.repositories._internal.router import router
from app.modules.repositories._internal.schemas import (
    RepositoryCreate,
    RepositoryDocumentOut,
    RepositoryOut,
    RepositoryVersionOut,
)
from app.modules.repositories._internal.service import (
    NormalizedDocument,
    archive_repository,
    create_repository,
    get_documents,
    get_repository,
    hard_delete_repository,
    ingest_version,
    list_repositories,
    list_versions,
    soft_delete_repository,
)

__all__ = [
    "NormalizedDocument",
    "RepositoryCreate",
    "RepositoryDocumentOut",
    "RepositoryOut",
    "RepositoryVersionOut",
    "archive_repository",
    "create_repository",
    "get_documents",
    "get_repository",
    "hard_delete_repository",
    "ingest_version",
    "list_repositories",
    "list_versions",
    "router",
    "soft_delete_repository",
]
