"""Public API of the publishing module (Sprint 6).

Planned surface:
  - create_publish_job(test_case_ids, target) -> job_id
  - get_job(job_id)

PublishAdapter interface; Jira-native adapter for MVP. Xray/Zephyr adapters
land in V1/V2 behind the same interface. Partial-success is first-class.
Implemented in Sprint 6.
"""

from __future__ import annotations

__all__: list[str] = []
