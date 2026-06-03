"""Public API of the test_generation module (Sprint 5).

Planned surface:
  - start_generation(scope, scope_ref, format) -> run_id
  - get_run / list_test_cases / approve(test_case_id)

Planner + executor flow with per-story fan-out and partial-success handling.
MVP formats: manual, bdd. Owns generation_runs, test_cases. Implemented Sprint 5.
"""

from __future__ import annotations

__all__: list[str] = []
