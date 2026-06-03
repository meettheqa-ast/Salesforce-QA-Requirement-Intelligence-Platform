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

__all__: list[str] = []
