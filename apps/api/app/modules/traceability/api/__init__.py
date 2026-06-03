"""Public API of the traceability module (Sprint 5 capture, V1 UI).

Planned surface:
  - add_edge(source, target, edge_type)
  - query_edges(...) / coverage_for(repository_id) [V1]

Edges (requirement -> AC -> test) are captured at generation time in Sprint 5;
coverage matrix and gap reports are V1. Owns traces.
"""

from __future__ import annotations

__all__: list[str] = []
