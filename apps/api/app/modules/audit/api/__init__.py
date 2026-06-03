"""Public API of the audit module.

Other modules import ONLY from here. See docs/AGENTS.md.
"""

from __future__ import annotations

from app.modules.audit._internal.service import emit, list_events

__all__ = ["emit", "list_events"]
