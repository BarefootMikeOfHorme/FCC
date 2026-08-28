"""
bottom.py

Unified baseline monitoring layer.

Phase 1:
- Wraps system_metrics, providers, terminal_monitors
- Exposes a single snapshot() API
- Provides safe-to-fail behavior
- Uses BtHop (btop) as fallback mode when needed

Designed to be:
- Self-contained
- L1-compatible but L1-agnostic
- Ready to replace system_metrics/providers/terminal_monitors later
"""

from typing import Dict, Any, Optional

from .system_metrics import SystemMetrics
from .providers import MonitoringProviderRegistry
from .terminal_monitors import TerminalMonitorManager
from .btop_launcher import launch_btop


class BottomMonitor:
    """
    Unified baseline monitor.

    Current behavior:
    - Collects system metrics via SystemMetrics
    - Collects provider metrics via MonitoringProviderRegistry
    - Reports terminal monitor availability via TerminalMonitorManager
    - Provides a single snapshot() entrypoint
    - Offers a fallback_to_bthop() method for BtHop mode
    """

    def __init__(self) -> None:
        self._system = SystemMetrics()
        self._providers = MonitoringProviderRegistry()
        self._terminals = TerminalMonitorManager()
        self._initialized = False

    def initialize(self) -> None:
        """
        Initialize underlying subsystems.

        Safe to call multiple times.
        """
        if self._initialized:
            return
        try:
            self._system.initialize()
        except Exception:
            # System metrics init failure should not break baseline
            pass

        try:
            self._providers.initialize()
        except Exception:
            # Provider init failure should not break baseline
            pass

        # Terminal monitors are lazy; no init required
        self._initialized = True

    def snapshot(self) -> Dict[str, Any]:
        """
        Return a unified baseline snapshot.

        Structure:
        {
            "system": {...},
            "providers": {...},
            "terminal": {...},
            "status": "ok" | "degraded"
        }

        All failures are contained; never raises.
        """
        status = "ok"

        try:
            system = self._system.collect()
        except Exception:
            system = {"error": "system_metrics_failed"}
            status = "degraded"

        try:
            providers = self._providers.collect()
        except Exception:
            providers = {"error": "provider_metrics_failed"}
            status = "degraded"

        try:
            terminal = self._terminals.status()
        except Exception:
            terminal = {"error": "terminal_status_failed"}
            status = "degraded"

        return {
            "system": system,
            "providers": providers,
            "terminal": terminal,
            "status": status,
        }

    def fallback_to_bthop(self) -> str:
        """
        Enter BtHop (btop) fallback mode.

        This is the "bottom line" fallback:
        - If richer monitoring fails or is unavailable,
          BtHop can still be launched for manual inspection.

        Returns a human-readable status string.
        """
        try:
            result = launch_btop()
        except Exception as e:
            return f"BtHop fallback failed: {e}"
        return f"BtHop fallback: {result}"

    # Optional hook for future L1 integration:
    def as_event(self) -> Dict[str, Any]:
        """
        Represent the current snapshot as a monitoring event.

        This can be used by any event bus / logger / L1 engine
        without creating a hard dependency.
        """
        snap = self.snapshot()
        return {
            "type": "monitoring.bottom.snapshot",
            "data": snap,
        }


# Convenience factory
def create_bottom_monitor() -> BottomMonitor:
    monitor = BottomMonitor()
    monitor.initialize()
    return monitor
