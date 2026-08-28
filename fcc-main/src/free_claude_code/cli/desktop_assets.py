"""Packaged visual assets owned by the FCC desktop shell."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Optional

# Optional diagnostics hook (safe-to-fail)
try:
    from free_claude_code.core.system_diagnostics import diagnose_system
except Exception:
    diagnose_system = None

# Optional logging hook (safe-to-fail)
try:
    from free_claude_code.core.logging_integration import log_with_context
except Exception:
    log_with_context = None


_ICON_FILES = {
    ".icns": "app-icon.icns",
    ".ico": "app-icon.ico",
    ".png": "app-icon.png",
}

# Optional future-ready multi-format asset map
_EXTRA_ASSETS = {
    ".svg": "app-icon.svg",
    ".webp": "app-icon.webp",
}


def _resolve_icon_filename(suffix: str) -> str:
    """Resolve icon filename, supporting future formats."""
    normalized = suffix.lower()

    # Primary formats
    if normalized in _ICON_FILES:
        return _ICON_FILES[normalized]

    # Optional extended formats
    if normalized in _EXTRA_ASSETS:
        return _EXTRA_ASSETS[normalized]

    supported = ", ".join(sorted(_ICON_FILES | _EXTRA_ASSETS))
    raise ValueError(
        f"Unsupported app icon format {suffix!r}; expected one of: {supported}"
    )


def app_icon_bytes(suffix: str) -> bytes:
    """Read the packaged app icon matching a native file suffix."""
    try:
        filename = _resolve_icon_filename(suffix)
        return files("free_claude_code").joinpath("assets", filename).read_bytes()
    except Exception as exc:
        # Optional logging
        if log_with_context:
            try:
                log_with_context(
                    f"Failed to load desktop asset: {exc}",
                    level="error",
                    suffix=suffix,
                )
            except Exception:
                pass
        raise


def export_app_icon(destination: Path) -> None:
    """Copy the packaged native icon to an installer-owned destination."""
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(app_icon_bytes(destination.suffix))
    except Exception as exc:
        # Optional diagnostics hook
        if diagnose_system:
            try:
                diagnose_system()
            except Exception:
                pass

        # Optional logging
        if log_with_context:
            try:
                log_with_context(
                    f"Failed to export desktop icon: {exc}",
                    level="error",
                    destination=str(destination),
                )
            except Exception:
                pass

        raise
