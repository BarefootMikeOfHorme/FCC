"""
GPU monitoring (NVIDIA, AMD, Intel where possible).

This module is intentionally lightweight:
- Uses GPUtil when available
- Returns structured GPU metrics
- Never raises exceptions to callers
- Safe to register into monitoring providers
"""

from __future__ import annotations

from typing import Dict, Any

try:
    import GPUtil  # optional dependency
except ImportError:
    GPUtil = None


class GPUMetrics:
    def initialize(self) -> None:
        """Optional initialization hook (currently a no-op)."""
        pass

    def collect(self) -> Dict[str, Any]:
        """Collect GPU metrics using GPUtil if available."""
        if GPUtil is None:
            return {"error": "GPUtil_not_available"}

        try:
            gpus = GPUtil.getGPUs()
        except Exception as e:
            return {"error": f"gpu_query_failed: {e}"}

        data = []
        for gpu in gpus:
            data.append(
                {
                    "id": gpu.id,
                    "name": gpu.name,
                    "load": gpu.load,
                    "memory_used": gpu.memoryUsed,
                    "memory_total": gpu.memoryTotal,
                    "temperature": gpu.temperature,
                }
            )

        return {"gpus": data}
