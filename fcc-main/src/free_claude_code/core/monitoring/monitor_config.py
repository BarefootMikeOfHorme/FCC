"""
monitor_config.py

Toggleable config for monitors.

Simple in-memory config; you can later back it with a file or env.
"""

from typing import Dict, Any


class MonitorConfig:
    def __init__(self) -> None:
        self._flags: Dict[str, Any] = {
            "enable_gpu_metrics": True,
            "enable_model_metrics": True,
            "enable_bottom": True,
        }

    def set(self, key: str, value: Any) -> None:
        self._flags[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._flags.get(key, default)

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._flags)
