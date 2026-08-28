"""
btop Launcher

Thin wrapper around TerminalMonitorManager-style behavior,
exposed as a standalone function for direct CLI/Admin use.
"""

import subprocess
import shutil


def launch_btop() -> str:
    path = shutil.which("btop")
    if not path:
        return "btop not installed."
    try:
        subprocess.Popen([path])
        return "btop launched."
    except Exception as e:
        return f"Failed to launch btop: {e}"
