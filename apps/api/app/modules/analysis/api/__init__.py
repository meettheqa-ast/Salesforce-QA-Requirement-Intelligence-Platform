"""Public API of the analysis module (Sprint 3).

Planned surface:
  - start_analysis(scope, scope_ref) -> run_id
  - get_run(run_id) / list_findings(run_id, filter)

Two-stage: cheap-model triage then primary-model deep analysis. Findings carry
category, severity, citations, confidence. Owns analysis_runs, findings.
Implemented in Sprint 3.
"""

from __future__ import annotations

__all__: list[str] = []
