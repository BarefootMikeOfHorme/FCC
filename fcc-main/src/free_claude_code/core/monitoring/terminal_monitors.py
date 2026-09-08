"""
Terminal Monitor Manager

Handles launching external terminal-based monitors:
- btop
- glances
- htop
- bottom (BoHTOM launcher)

Non-blocking, best-effort, and never critical to core/L1.
"""

import subprocess
import shutil
import platform
from typing import Dict, Optional
from loguru import logger

# ============================================================
# ORIGINAL CLASS (kept exactly as-is)
# ============================================================

class TerminalMonitorManager:
    def __init__(self) -> None:
        # Detect external terminal tools
        self.available: Dict[str, str] = {
            "btop": shutil.which("btop"),
            "glances": shutil.which("glances"),
            "htop": shutil.which("htop"),

            # bottom is NOT a system binary, so we mark it as "internal"
            # and handle it separately in launch()
            "bottom": "internal"
        }

    def status(self) -> Dict[str, str]:
        """Return availability of terminal monitors."""
        return dict(self.available)

    def launch(self, name: str) -> str:
        """Launch a terminal monitor if available."""
        if name not in self.available:
            return f"Unknown monitor: {name}"

        if name == "bottom":
            try:
                # LOCAL IMPORT — breaks circular import
                from .bottom_launcher import launch_bottom
                return launch_bottom()
            except Exception as e:
                return f"Failed to launch bottom monitor: {e}"

        path = self.available[name]
        if not path:
            return f"{name} is not installed."

        try:
            subprocess.Popen([path])
            return f"Launched {name}"
        except Exception as e:
            return f"Failed to launch {name}: {e}"


# ============================================================
# ENHANCED CLASS — OPTIONAL, NON-BREAKING, ADDITIVE
# ============================================================

class EnhancedTerminalMonitorManager(TerminalMonitorManager):
    """
    Enhanced version of TerminalMonitorManager.

    Adds:
    - structured logging
    - instance tagging
    - unified return objects
    - fallback monitor launching
    - batch launching
    - Windows terminal support
    - safe-mode error handling
    """

    def __init__(self, instance_id: Optional[str] = None) -> None:
        super().__init__()
        self.instance_id = instance_id or "default"
        logger.info(f"[Monitor] EnhancedTerminalMonitorManager initialized (instance={self.instance_id})")

    def _launch_external(self, name: str, path: str) -> Dict[str, str]:
        """Launch external binary monitors with Windows terminal support."""
        try:
            if platform.system().lower() == "windows":
                subprocess.Popen(["wt.exe", path])
            else:
                subprocess.Popen([path])

            logger.info(f"[Monitor] Launched {name} (instance={self.instance_id})")

            return {
                "monitor": name,
                "status": "launched",
                "path": path,
                "instance": self.instance_id,
            }
        except Exception as e:
            logger.error(f"[Monitor] Failed to launch {name}: {e}")
            return {
                "monitor": name,
                "status": "error",
                "error": str(e),
                "instance": self.instance_id,
            }

    def launch(self, name: str) -> Dict[str, str]:
        """Launch a terminal monitor with structured output."""
        if name not in self.available:
            return {"monitor": name, "status": "unknown", "instance": self.instance_id}

        if name == "bottom":
            try:
                # LOCAL IMPORT — breaks circular import
                from .bottom_launcher import launch_bottom
                launch_bottom()
                logger.info(f"[Monitor] Launched bottom (instance={self.instance_id})")
                return {
                    "monitor": "bottom",
                    "status": "launched",
                    "path": "internal",
                    "instance": self.instance_id,
                }
            except Exception as e:
                logger.error(f"[Monitor] Failed to launch bottom: {e}")
                return {
                    "monitor": "bottom",
                    "status": "error",
                    "error": str(e),
                    "instance": self.instance_id,
                }

        path = self.available[name]
        if not path:
            logger.warning(f"[Monitor] {name} not installed (instance={self.instance_id})")
            return {
                "monitor": name,
                "status": "missing",
                "instance": self.instance_id,
            }

        return self._launch_external(name, path)

    def launch_all(self) -> Dict[str, Dict[str, str]]:
        """Launch all available monitors."""
        results = {}
        for name, path in self.available.items():
            results[name] = self.launch(name)
        return results


# ============================================================
# FCC-SERVER EXPECTED ENTRYPOINT (UPSTREAM COMPATIBLE)
# ============================================================

def start_monitoring():
    """
    FCC-server expects this function name.
    We route it to the enhanced monitoring cluster.
    """
    manager = EnhancedTerminalMonitorManager(instance_id="fcc-server")
    manager.launch_all()
