"""Canonical installed Free Claude Code package version.

This FCC‑grade enhanced module provides:

- Backwards‑compatible `package_version() -> str`.
- Safe‑to‑fail metadata resolution with structured logging.
- Optional trace events for diagnostics and monitoring.
- Lightweight caching to avoid repeated metadata lookups.
- Fallbacks for source‑only installs, editable installs, and missing metadata.
"""

from __future__ import annotations

from functools import lru_cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version

# ---------------------------------------------------------------------------
# FCC core integrations (best‑effort)
# ---------------------------------------------------------------------------

try:
    from .logging_integration import log_with_context  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    def log_with_context(message: str, level: str = "info", **ctx: object) -> None:  # type: ignore[func-returns-value]
        return

try:
    from .trace import trace_event  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    def trace_event(event: str, **fields: object) -> None:  # type: ignore[func-returns-value]
        return


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DISTRIBUTION_NAME = "free-claude-code"
_UNKNOWN_VERSION = "0+unknown"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _log_version_failure(exc: Exception) -> None:
    """Emit a structured warning when version metadata cannot be resolved."""
    log_with_context(
        "FCC package version metadata unavailable; using fallback.",
        level="warning",
        error_type=type(exc).__name__,
        error=str(exc),
        distribution=_DISTRIBUTION_NAME,
    )


def _trace_version(version: str, *, outcome: str) -> None:
    """Emit a trace event for version resolution."""
    trace_event(
        "version.resolve",
        outcome=outcome,
        version=version,
        distribution=_DISTRIBUTION_NAME,
    )


# ---------------------------------------------------------------------------
# Core version resolver (cached)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _resolve_version() -> str:
    """Resolve the installed FCC package version with full FCC safety.

    This function is cached so repeated calls are free.
    """
    try:
        version = distribution_version(_DISTRIBUTION_NAME)
        _trace_version(version, outcome="ok")
        return version
    except PackageNotFoundError as exc:
        _log_version_failure(exc)
        _trace_version(_UNKNOWN_VERSION, outcome="fallback")
        return _UNKNOWN_VERSION
    except Exception as exc:  # noqa: BLE001
        # Any unexpected metadata failure should not break FCC.
        _log_version_failure(exc)
        _trace_version(_UNKNOWN_VERSION, outcome="error")
        return _UNKNOWN_VERSION


# ---------------------------------------------------------------------------
# Public API (backwards compatible)
# ---------------------------------------------------------------------------


def package_version() -> str:
    """Return installed metadata, or an explicit source-only fallback.

    Backwards-compatible wrapper around the enhanced resolver.
    """
    return _resolve_version()
