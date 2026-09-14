"""Public messaging session persistence API.

This module re-exports `SessionStore`, the canonical persistence layer
used by ApplicationRuntime and messaging/session orchestration.
"""

from __future__ import annotations

from .store import SessionStore

# Public API surface for session persistence
__all__ = ["SessionStore"]
