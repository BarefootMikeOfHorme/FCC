from typing import Dict, Any

"""
monitor_config.py

Toggleable configuration for monitoring components.
Simple in-memory config; can later be backed by a file or environment variables.
"""


class MonitorConfig:
    def __init__(self) -> None:
        self._flags: Dict[str, Any] = {
            "enable_gpu_metrics": True,
            "enable_model_metrics": True,
            "enable_bottom": True,
        }

    def set(self, key: str, value: Any) -> None:
        """Set a configuration flag."""
        self._flags[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration flag."""
        return self._flags.get(key, default)

    def as_dict(self) -> Dict[str, Any]:
        """Return all flags as a dictionary."""
        return dict(self._flags)
