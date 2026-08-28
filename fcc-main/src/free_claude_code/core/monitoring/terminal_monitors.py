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
from typing import Dict

# Import your bottom launcher
from .bottom_launcher import launch_bottom


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
        """
        Return availability of terminal monitors.

        For bottom:
        - "internal" means it is always available
        """
        return dict(self.available)

    def launch(self, name: str) -> str:
        """
        Launch a terminal monitor if available.

        Special case:
        - bottom uses the internal launcher, not a system binary
        """
        if name not in self.available:
            return f"Unknown monitor: {name}"

        # Handle bottom (BoHTOM launcher)
        if name == "bottom":
            try:
                return launch_bottom()
            except Exception as e:
                return f"Failed to launch bottom monitor: {e}"

        # Handle external binaries
        path = self.available[name]
        if not path:
            return f"{name} is not installed."

        try:
            subprocess.Popen([path])
            return f"Launched {name}"
        except Exception as e:
            return f"Failed to launch {name}: {e}"