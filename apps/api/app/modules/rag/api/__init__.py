"""Public API of the rag module (Sprint 3).

Planned surface:
  - embed_documents(version_id)
  - retrieve(repository_id, version_id, query, filters, top_k) -> chunks
  - query_plan(text) -> structured retrieval plan

Hybrid retrieval: pgvector (semantic) + Postgres tsvector (lexical) + RRF.
StubEmbeddingsProvider when EMBEDDINGS_PROVIDER=stub. Implemented in Sprint 3.
"""

from __future__ import annotations

__all__: list[str] = []
