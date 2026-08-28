"""
gpu_metrics.py

GPU monitoring (NVIDIA, AMD, Intel where possible).

Standalone helper; you can register it into providers later.
"""

from typing import Dict, Any

try:
    import GPUtil  # optional dependency
except ImportError:
    GPUtil = None


class GPUMetrics:
    def initialize(self) -> None:
        # No-op for now; hook for future init
        pass

    def collect(self) -> Dict[str, Any]:
        if GPUtil is None:
            return {"error": "GPUtil_not_available"}

        try:
            gpus = GPUtil.getGPUs()
        except Exception as e:
            return {"error": f"gpu_query_failed: {e}"}

        data = []
        for gpu in gpus:
            data.append({
                "id": gpu.id,
                "name": gpu.name,
                "load": gpu.load,
                "memory_used": gpu.memoryUsed,
                "memory_total": gpu.memoryTotal,
                "temperature": gpu.temperature,
            })

        return {"gpus": data}
