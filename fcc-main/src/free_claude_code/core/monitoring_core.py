\"\"\"FCC Core Monitoring System
Structured metric sampling + safe-to-fail collectors + orchestrator integration.
\"\"\"

import time
import psutil
import threading
from typing import Optional, Dict, Any

# FCC integrations
try:
    from .trace import trace_event
except Exception:
    def trace_event(event: str, **fields: object) -> None:
        return

try:
    from .logging_integration import log_with_context
except Exception:
    def log_with_context(message: str, level: str = "info", **ctx: object) -> None:
        return

try:
    from .output_schemas import SystemMetrics, MetricPoint
except Exception:
    # Minimal fallback types
    class MetricPoint:
        def __init__(self, name: str, value: float, timestamp: float):
            self.name = name
            self.value = value
            self.timestamp = timestamp

    class SystemMetrics:
        def __init__(self, cpu: float, memory: float, disk: float, net_in: float, net_out: float, timestamp: float):
            self.cpu = cpu
            self.memory = memory
            self.disk = disk
            self.net_in = net_in
            self.net_out = net_out
            self.timestamp = timestamp


class FCCMonitoringCore:
    \"\"\"FCC Core Monitoring System.

    Provides:
    - Structured metric sampling
    - Safe-to-fail collectors
    - Integration with SystemMetrics + MetricPoint
    - Background sampling thread
    - Orchestrator + admin UI compatibility
    \"\"\"

    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_net = None

        trace_event("monitoring_core.init", interval=self.interval)

    def _sample_network(self) -> Dict[str, float]:
        try:
            counters = psutil.net_io_counters()
            if self._last_net is None:
                self._last_net = counters
                return {"in": 0.0, "out": 0.0}

            delta_in = counters.bytes_recv - self._last_net.bytes_recv
            delta_out = counters.bytes_sent - self._last_net.bytes_sent
            self._last_net = counters

            return {"in": float(delta_in), "out": float(delta_out)}
        except Exception as e:
            log_with_context("Network sampling failed.", level="warning", error=str(e))
            return {"in": 0.0, "out": 0.0}

    def _sample_once(self) -> SystemMetrics:
        timestamp = time.time()

        try:
            cpu = psutil.cpu_percent(interval=None)
        except Exception:
            cpu = 0.0

        try:
            memory = psutil.virtual_memory().percent
        except Exception:
            memory = 0.0

        try:
            disk = psutil.disk_usage("/").percent
        except Exception:
            disk = 0.0

        net = self._sample_network()

        metrics = SystemMetrics(
            cpu=cpu,
            memory=memory,
            disk=disk,
            net_in=net["in"],
            net_out=net["out"],
            timestamp=timestamp,
        )

        trace_event(
            "monitoring_core.sample",
            cpu=cpu,
            memory=memory,
            disk=disk,
            net_in=net["in"],
            net_out=net["out"],
            timestamp=timestamp,
        )

        return metrics

    def _run(self):
        log_with_context("Monitoring core started.", level="info")
        while self._running:
            try:
                metrics = self._sample_once()
                # Future: push to orchestrator, admin UI, dashboard
            except Exception as e:
                log_with_context("Monitoring sample failed.", level="error", error=str(e))
            time.sleep(self.interval)
        log_with_context("Monitoring core stopped.", level="info")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        trace_event("monitoring_core.start")

    def stop(self):
        if not self._running:
            return
        self._running = False
        trace_event("monitoring_core.stop")
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None


monitoring_core = FCCMonitoringCore()
