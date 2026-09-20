from .btop_launcher import launch_btop
from .providers import MonitoringProviderRegistry
from .system_metrics import SystemMetrics
from .terminal_monitors import TerminalMonitorManager
from typing import Dict, Any
"""
bottom.py

Unified baseline monitoring layer (BoHTOM).

- Wraps system_metrics, providers, terminal_monitors
- Exposes snapshot() API
- Safe-to-fail
- BtHop fallback
"""




class BottomMonitor:
    def __init__(self) -> None:
        self._system = SystemMetrics()
        self._providers = MonitoringProviderRegistry()
        self._terminals = TerminalMonitorManager()
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        try:
            self._system.initialize()
        except Exception:
            pass
        try:
            self._providers.initialize()
        except Exception:
            pass
        self._initialized = True

    def snapshot(self) -> Dict[str, Any]:
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
        try:
            return launch_btop()
        except Exception as e:
            return f"BtHop fallback failed: {e}"

    def as_event(self) -> Dict[str, Any]:
        return {
            "type": "monitoring.bottom.snapshot",
            "data": self.snapshot(),
        }


def create_bottom_monitor() -> BottomMonitor:
    m = BottomMonitor()
    m.initialize()
    return m
