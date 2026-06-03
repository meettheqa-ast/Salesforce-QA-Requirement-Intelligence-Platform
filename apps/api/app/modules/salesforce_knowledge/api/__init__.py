"""Public API of the salesforce_knowledge module (Sprint 3).

Planned surface:
  - get_salesforce_context(text, task_type) -> SalesforceContext
  - ingest_source_version(source_id, version)
  - list_reasoning_patterns(cloud, task)

Tier 1 (shared docs index) + Tier 2 (reasoning patterns) for MVP, covering
Sales Cloud + Service Cloud. Cloud classifier (rules + cheap LLM verify).
Implemented in Sprint 3.
"""

from __future__ import annotations

__all__: list[str] = []
