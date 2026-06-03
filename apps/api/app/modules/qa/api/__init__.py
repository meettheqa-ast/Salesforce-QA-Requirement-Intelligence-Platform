"""Public API of the qa module (Sprint 4).

Planned surface:
  - start_session(repository_id) -> session_id
  - ask(session_id, question) -> answer (with citations)
  - get_history(session_id)

Retrieval-driven answering with mandatory citations and rolling conversation
memory. Owns qa_sessions, qa_messages. Implemented in Sprint 4.
"""

from __future__ import annotations

__all__: list[str] = []
