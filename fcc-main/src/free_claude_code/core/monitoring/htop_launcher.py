"""
htop Launcher

Thin wrapper for direct use.
"""

import subprocess
import shutil


def launch_htop() -> str:
    path = shutil.which("htop")
    if not path:
        return "htop not installed."
    try:
        subprocess.Popen([path])
        return "htop launched."
    except Exception as e:
        return f"Failed to launch htop: {e}"
