"""Markdown rendering utilities for messaging platforms.

This package exposes the public rendering interfaces used by the messaging
workflow. Individual renderers (Discord, Telegram, Markdown tables, etc.)
are implemented in submodules and re-exported here when appropriate.
"""

from __future__ import annotations

# Public API surface for rendering utilities
__all__: list[str] = []
