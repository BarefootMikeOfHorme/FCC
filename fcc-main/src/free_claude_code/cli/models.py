"""Model listing utilities for FCC CLI."""

from __future__ import annotations

from free_claude_code.runtime.provider_manager import ProviderManager

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

# Optional orchestrator hook (safe-to-fail)
try:
    from free_claude_code.cli.monitoring_orchestrator import monitoring_ready
except Exception:
    monitoring_ready = None


def list_models() -> None:
    """List reachable models only, with safe-to-fail diagnostics and logging."""

    try:
        pm = ProviderManager()
        models = pm.get_all_models()
    except Exception as exc:
        # Optional logging
        if log_with_context:
            try:
                log_with_context(
                    f"Failed to enumerate models: {exc}",
                    level="error",
                )
            except Exception:
                pass

        # Optional diagnostics
        if diagnose_system:
            try:
                diagnose_system()
            except Exception:
                pass

        raise

    print("[FCC] Models:")
    for m in models:
        print(f"- {m}")

    # Optional orchestrator readiness signal
    if monitoring_ready:
        try:
            monitoring_ready()
        except Exception:
            pass
