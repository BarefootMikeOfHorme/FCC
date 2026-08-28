"""
Monitoring Orchestrator

Coordinates and unifies:
- System metrics
- Provider metrics
- Terminal monitors
- Bottom unified baseline monitor (BoHTOM)
- Event emission for diagnostics/logging

Architectural Guarantees:
- Self-contained:
    All monitoring logic is encapsulated within the monitoring subsystem.
    No external dependencies on L1 internals, protocol engines, or UI layers.

- L1-compatible but L1-agnostic:
    The orchestrator exposes stable, predictable APIs usable by L1 schedulers,
    protocol engines, or any higher-level automation — without depending on
    L1-specific structures, message formats, or runtime assumptions.

- Safe to call from CLI, Admin UI, or protocol engines:
    All operations are exception-safe, fire-and-forget, and designed so that
    monitoring failures never propagate upward or disrupt core system behavior.

Supports dual-mode bottom operation:
- "additional" (default): bottom is included alongside legacy monitors
- "primary": bottom becomes the main unified snapshot source
"""

from typing import Callable, Dict, List, Any

from .system_metrics import SystemMetrics
from .terminal_monitors import TerminalMonitorManager
from .providers import MonitoringProviderRegistry
from .bottom import BottomMonitor
from .monitor_config import MonitorConfig


class MonitoringOrchestrator:
    """
    Main monitoring coordinator.

    Responsibilities:
    - initialize(): prepare all monitoring subsystems
    - snapshot(): produce unified monitoring view (dual-mode bottom support)
    - tick(): periodic update hook for schedulers or loops
    - launch_terminal(): start external monitors (including bottom)
    - subscribe(): register event listeners
    - emit(): dispatch monitoring events safely

    Architectural Guarantees:
    - Self-contained: no external coupling; all monitoring logic lives here.
    - L1-compatible: callable from L1 schedulers and protocol engines.
    - L1-agnostic: does not depend on L1 internals or message formats.
    - Safe for CLI/Admin UI: fire-and-forget, exception-safe event emission.
    """

    def __init__(self) -> None:
        self.metrics = SystemMetrics()
        self.terminals = TerminalMonitorManager()
        self.providers = MonitoringProviderRegistry()
        self.bottom = BottomMonitor()
        self.config = MonitorConfig()  # NEW: dual-mode control

        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._initialized = False

    def initialize(self) -> None:
        """Initialize monitoring subsystems."""
        if self._initialized:
            return

        # Legacy subsystems
        self.metrics.initialize()
        self.providers.initialize()

        # Bottom unified baseline monitor
        try:
            self.bottom.initialize()
        except Exception:
            # Bottom is safe-to-fail
            pass

        self._initialized = True

    def snapshot(self) -> Dict[str, Any]:
        """
        Dual-mode snapshot:
        - additional: legacy + bottom
        - primary: bottom only
        """
        mode = self.config.get("monitor_mode", "additional")

        # PRIMARY MODE → bottom is the main monitor
        if mode == "primary":
            try:
                bottom_snap = self.bottom.snapshot()
            except Exception:
                bottom_snap = {"error": "bottom_snapshot_failed"}

            self.emit({"type": "monitoring.snapshot", "data": bottom_snap})
            return bottom_snap

        # ADDITIONAL MODE → legacy + bottom
        system = self.metrics.collect()
        providers = self.providers.collect()
        terminal = self.terminals.status()

        try:
            bottom_snap = self.bottom.snapshot()
        except Exception:
            bottom_snap = {"error": "bottom_snapshot_failed"}

        snapshot = {
            "system": system,
            "providers": providers,
            "terminal": terminal,
            "bottom": bottom_snap,
        }

        self.emit({"type": "monitoring.snapshot", "data": snapshot})
        return snapshot

    def tick(self) -> Dict[str, Any]:
        """Periodic update hook."""
        return self.snapshot()

    def launch_terminal(self, name: str) -> str:
        """
        Launch a terminal monitor by name.

        Supported names:
        - "btop"
        - "glances"
        - "htop"
        - "bottom"
        """
        result = self.terminals.launch(name)

        self.emit({
            "type": "monitoring.terminal.launch",
            "data": {"name": name, "result": result}
        })

        if name == "bottom":
            self.emit({
                "type": "monitoring.bottom.launch",
                "data": {"result": result}
            })

        return result

    def subscribe(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Register an event listener."""
        if listener not in self._subscribers:
            self._subscribers.append(listener)

    def unsubscribe(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Remove a previously registered listener."""
        if listener in self._subscribers:
            self._subscribers.remove(listener)

    def emit(self, event: Dict[str, Any]) -> None:
        """
        Emit an event to all subscribers.

        Fire-and-forget, exception-safe.
        """
        for listener in list(self._subscribers):
            try:
                listener(event)
            except Exception:
                continue
