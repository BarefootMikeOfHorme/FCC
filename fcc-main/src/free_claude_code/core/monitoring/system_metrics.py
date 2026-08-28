"""
System Metrics Collector

Collects:
- CPU usage
- RAM usage
- Disk usage
- Network I/O
- Basic OS info

Designed to be:
- Lightweight
- Safe
- Always available (psutil-based)
"""

import psutil
import platform
import time
from typing import Dict, Any


class SystemMetrics:
    def initialize(self) -> None:
        """Placeholder for future initialization (GPU, advanced metrics, etc.)."""
        # No-op for now; kept for future expansion.
        pass

    def collect(self) -> Dict[str, Any]:
        """Collect system metrics snapshot."""
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()._asdict()
            disk = psutil.disk_usage("/")._asdict()
            net = psutil.net_io_counters()._asdict()
        except Exception:
            # In case of any psutil failure, return minimal info
            cpu = None
            ram = {}
            disk = {}
            net = {}

        return {
            "timestamp": time.time(),
            "cpu": cpu,
            "ram": ram,
            "disk": disk,
            "network": net,
            "system": {
                "platform": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
            },
        }
