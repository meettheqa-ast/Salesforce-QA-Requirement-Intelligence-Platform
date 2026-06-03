"""Public API of the auth module."""

from __future__ import annotations

from app.modules.auth._internal.dependencies import (
    get_current_principal,
    require_role,
)
from app.modules.auth._internal.providers import AuthError, Principal
from app.modules.auth._internal.router import router

__all__ = [
    "AuthError",
    "Principal",
    "get_current_principal",
    "require_role",
    "router",
]
