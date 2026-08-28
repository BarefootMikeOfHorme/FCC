"""
model_metrics.py

LLM/model load/latency/error monitoring.

This is a generic stub; you can wire it to your actual
model runner / orchestration layer later.
"""

from typing import Dict, Any
import time


class ModelMetrics:
    def __init__(self) -> None:
        self._last_latency: float | None = None
        self._last_error: str | None = None
        self._active_models: int = 0

    def initialize(self) -> None:
        pass

    def record_call(self, latency_seconds: float, error: str | None = None) -> None:
        self._last_latency = latency_seconds
        self._last_error = error

    def set_active_models(self, count: int) -> None:
        self._active_models = count

    def collect(self) -> Dict[str, Any]:
        return {
            "timestamp": time.time(),
            "active_models": self._active_models,
            "last_latency": self._last_latency,
            "last_error": self._last_error,
        }
