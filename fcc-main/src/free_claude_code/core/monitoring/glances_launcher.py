"""
glances Launcher

Thin wrapper for direct use.
"""

import subprocess
import shutil


def launch_glances() -> str:
    path = shutil.which("glances")
    if not path:
        return "glances not installed."
    try:
        subprocess.Popen([path])
        return "glances launched."
    except Exception as e:
        return f"Failed to launch glances: {e}"
