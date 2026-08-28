"""Lightweight entrypoint for the optional FCC desktop shell."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from free_claude_code.cli.desktop_assets import export_app_icon

# Optional orchestrator hook (safe-to-fail)
try:
    from free_claude_code.cli.monitoring_orchestrator import start_monitoring_orchestrator
except Exception:
    start_monitoring_orchestrator = None

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


def _print_usage() -> None:
    print("Usage: fcc-desktop [--export-icon PATH]", file=sys.stderr)


def launch(argv: Sequence[str] | None = None) -> None:
    """Export installer assets or launch the supported native tray adapter."""

    args = tuple(sys.argv[1:] if argv is None else argv)

    # Handle icon export mode
    if len(args) == 2 and args[0] == "--export-icon":
        try:
            export_app_icon(Path(args[1]))
        except Exception as exc:
            if log_with_context:
                try:
                    log_with_context(
                        f"Failed to export icon: {exc}",
                        level="error",
                        destination=args[1],
                    )
                except Exception:
                    pass

            if diagnose_system:
                try:
                    diagnose_system()
                except Exception:
                    pass

            raise
        return

    # Invalid args
    if args:
        _print_usage()
        raise SystemExit(2)

    # Platform gating
    if sys.platform not in {"darwin", "win32"}:
        print("FCC Desktop is supported on Windows and macOS.", file=sys.stderr)
        raise SystemExit(1)

    # Optional orchestrator startup
    if start_monitoring_orchestrator:
        try:
            start_monitoring_orchestrator()
        except Exception:
            pass

    # Launch native tray adapter
    try:
        from free_claude_code.cli.desktop_tray import launch as launch_tray
        launch_tray()
    except Exception as exc:
        if log_with_context:
            try:
                log_with_context(
                    f"Desktop tray launch failed: {exc}",
                    level="error",
                )
            except Exception:
                pass

        if diagnose_system:
            try:
                diagnose_system()
            except Exception:
                pass

        raise
