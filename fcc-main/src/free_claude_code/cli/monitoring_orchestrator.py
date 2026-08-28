"""
FCC Monitoring Orchestrator

Responsibilities:
- React to runtime lifecycle hooks (runtime_initialized, provider_manager_ready, asgi_ready, bootstrap_complete).
- Maintain a lightweight monitoring state (monitors, metrics, dependency status).
- Integrate with core monitoring modules (dependency_resolver, system metrics, terminal monitors) without
  breaking FCC bootstrap.
- Provide snapshot access for Admin / Diagnostics UI.

This module is intentionally conservative:
- No long-running loops started automatically.
- No external commands executed automatically.
- All failures are safe-to-fail and logged via print/loguru.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Optional, List, Any
import threading
import time

from loguru import logger

# Core monitoring imports (safe-to-fail)
try:
    from free_claude_code.core.monitoring.dependency_resolver import (
        resolve_dependencies,
        write_resolution_log,
        explain_dependency,
        explain_env_issue,
        explain_task,
    )
except Exception as exc:
    logger.warning(
        "Monitoring orchestrator: dependency_resolver import failed: {}",
        exc,
    )
    resolve_dependencies = None
    write_resolution_log = None
    explain_dependency = None
    explain_env_issue = None
    explain_task = None


# ---------------------------------------------------------------------------
# Types and simple structures
# ---------------------------------------------------------------------------

@dataclass
class MonitorProcess:
    name: str
    kind: str  # "terminal", "web", "service"
    status: str  # "inactive", "starting", "running", "failed"
    last_error: Optional[str] = None


@dataclass
class OrchestratorSnapshot:
    runtime_ready: bool
    provider_manager_ready: bool
    asgi_ready: bool
    bootstrap_complete: bool
    monitors: Dict[str, Dict[str, Any]]
    dependency_plan: Optional[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Monitoring Orchestrator core
# ---------------------------------------------------------------------------

class MonitoringOrchestrator:
    """
    Central coordinator for FCC monitoring.

    This is intentionally minimal:
    - Tracks lifecycle readiness flags.
    - Tracks monitor processes (logical, not actual PIDs).
    - Optionally resolves dependencies and writes a log.
    - Provides snapshots for Admin / Diagnostics UI.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

        # Lifecycle flags
        self.runtime_ready: bool = False
        self.provider_manager_ready_flag: bool = False
        self.asgi_ready_flag: bool = False
        self.bootstrap_complete_flag: bool = False

        # Logical monitor registry (you can expand this later)
        self.monitors: Dict[str, MonitorProcess] = {
            "btop": MonitorProcess(name="btop", kind="terminal", status="inactive"),
            "bottom": MonitorProcess(name="bottom", kind="terminal", status="inactive"),
            "glances": MonitorProcess(name="glances", kind="terminal", status="inactive"),
            "grafana": MonitorProcess(name="grafana", kind="web", status="inactive"),
        }

        # Dependency resolution plan (optional)
        self._dependency_plan: Optional[Any] = None

        # Optional background tick thread (disabled by default)
        self._tick_thread: Optional[threading.Thread] = None
        self._tick_running: bool = False

    # ----------------------------------------------------------------------
    # Lifecycle integration
    # ----------------------------------------------------------------------

    def on_runtime_initialized(self, runtime: Any) -> None:
        with self._lock:
            self.runtime_ready = True
        logger.info("MonitoringOrchestrator: runtime initialized.")

    def on_provider_manager_ready(self, provider_manager: Any) -> None:
        with self._lock:
            self.provider_manager_ready_flag = True
        logger.info("MonitoringOrchestrator: provider manager ready.")

    def on_asgi_ready(self, asgi_app: Any) -> None:
        with self._lock:
            self.asgi_ready_flag = True
        logger.info("MonitoringOrchestrator: ASGI app ready.")

    def on_bootstrap_complete(self) -> None:
        with self._lock:
            self.bootstrap_complete_flag = True
        logger.info("MonitoringOrchestrator: bootstrap complete.")

        # Optional: resolve dependencies once at bootstrap completion
        if resolve_dependencies is not None:
            try:
                plan = resolve_dependencies()
                self._dependency_plan = plan
                logger.info(
                    "MonitoringOrchestrator: dependency resolution plan computed "
                    "(missing={}, issues={}).",
                    len(plan.missing_dependencies),
                    len(plan.env_issues),
                )
                # Optional: write a log next to FCC logs
                if write_resolution_log is not None:
                    write_resolution_log(plan, "dependency_resolver.jsonc")
            except Exception as exc:
                logger.warning(
                    "MonitoringOrchestrator: dependency resolution failed safely: {}",
                    exc,
                )

    # ----------------------------------------------------------------------
    # Monitor registry helpers (logical only)
    # ----------------------------------------------------------------------

    def set_monitor_status(
        self,
        name: str,
        status: str,
        error: Optional[str] = None,
    ) -> None:
        with self._lock:
            monitor = self.monitors.get(name)
            if not monitor:
                monitor = MonitorProcess(name=name, kind="terminal", status=status)
                self.monitors[name] = monitor
            monitor.status = status
            monitor.last_error = error

    # ----------------------------------------------------------------------
    # Snapshot / diagnostics
    # ----------------------------------------------------------------------

    def get_snapshot(self) -> OrchestratorSnapshot:
        with self._lock:
            monitors_dict = {
                name: asdict(monitor) for name, monitor in self.monitors.items()
            }

            plan_dict: Optional[Dict[str, Any]] = None
            if self._dependency_plan is not None:
                # Convert ResolutionPlan dataclass to dict
                plan = self._dependency_plan
                plan_dict = {
                    "missing_dependencies": [asdict(d) for d in plan.missing_dependencies],
                    "outdated_dependencies": [asdict(d) for d in plan.outdated_dependencies],
                    "env_issues": [asdict(e) for e in plan.env_issues],
                    "suggested_tasks": [asdict(t) for t in plan.suggested_tasks],
                }

            return OrchestratorSnapshot(
                runtime_ready=self.runtime_ready,
                provider_manager_ready=self.provider_manager_ready_flag,
                asgi_ready=self.asgi_ready_flag,
                bootstrap_complete=self.bootstrap_complete_flag,
                monitors=monitors_dict,
                dependency_plan=plan_dict,
            )

    # ----------------------------------------------------------------------
    # Optional tick loop (disabled by default)
    # ----------------------------------------------------------------------

    def start_tick_loop(self, interval_seconds: float = 5.0) -> None:
        """
        Start a lightweight background tick loop.

        Currently only logs heartbeat; you can extend this to:
        - refresh metrics
        - prune dead monitors
        - emit events
        """
        with self._lock:
            if self._tick_running:
                return
            self._tick_running = True

        def _loop() -> None:
            logger.info("MonitoringOrchestrator: tick loop started.")
            while True:
                with self._lock:
                    if not self._tick_running:
                        break
                    # Placeholder: you can add metrics refresh here.
                    logger.debug("MonitoringOrchestrator: tick.")
                time.sleep(interval_seconds)
            logger.info("MonitoringOrchestrator: tick loop stopped.")

        self._tick_thread = threading.Thread(
            target=_loop,
            name="MonitoringOrchestratorTick",
            daemon=True,
        )
        self._tick_thread.start()

    def stop_tick_loop(self) -> None:
        with self._lock:
            self._tick_running = False


# ---------------------------------------------------------------------------
# Global orchestrator instance
# ---------------------------------------------------------------------------

_orchestrator: Optional[MonitoringOrchestrator] = None


def _get_orchestrator() -> MonitoringOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MonitoringOrchestrator()
    return _orchestrator


# ---------------------------------------------------------------------------
# FCC bootstrap hooks (imported by runtime/bootstrap.py)
# ---------------------------------------------------------------------------

def runtime_initialized(runtime: Any) -> None:
    """
    Called by bootstrap after ApplicationRuntime is constructed.
    """
    orch = _get_orchestrator()
    try:
        orch.on_runtime_initialized(runtime)
    except Exception as exc:
        logger.warning("runtime_initialized hook failed safely: {}", exc)


def provider_manager_ready(provider_manager: Any) -> None:
    """
    Called by bootstrap after ProviderRuntimeManager is constructed.
    """
    orch = _get_orchestrator()
    try:
        orch.on_provider_manager_ready(provider_manager)
    except Exception as exc:
        logger.warning("provider_manager_ready hook failed safely: {}", exc)


def asgi_ready(asgi_app: Any) -> None:
    """
    Called by bootstrap after RuntimeASGIApp is constructed.
    """
    orch = _get_orchestrator()
    try:
        orch.on_asgi_ready(asgi_app)
    except Exception as exc:
        logger.warning("asgi_ready hook failed safely: {}", exc)


def bootstrap_complete() -> None:
    """
    Called by bootstrap after build_asgi_app() returns successfully.
    """
    orch = _get_orchestrator()
    try:
        orch.on_bootstrap_complete()
    except Exception as exc:
        logger.warning("bootstrap_complete hook failed safely: {}", exc)


# ---------------------------------------------------------------------------
# Admin / Diagnostics helpers (optional)
# ---------------------------------------------------------------------------

def get_monitoring_snapshot() -> Dict[str, Any]:
    """
    Helper for Admin / Diagnostics UI to fetch a JSON-serializable snapshot.
    """
    orch = _get_orchestrator()
    snap = orch.get_snapshot()
    return asdict(snap)
