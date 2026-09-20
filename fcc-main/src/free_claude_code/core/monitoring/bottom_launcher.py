"""
bottom_launcher.py

Launcher for the unified baseline monitor (BottomMonitor / BoHTOM).

This does NOT run the Python monitor inline — it opens a terminal window
running a lightweight “bottom snapshot viewer” so the user can inspect
live metrics without blocking the main FCC runtime.

Safe on Windows, Linux, macOS.
Never raises exceptions to callers.
"""

from __future__ import annotations

import subprocess
import sys
import os
from loguru import logger

# Local import to avoid circular dependency
from .bottom import BottomMonitor


def _viewer_script() -> str:
    """
    Generate a tiny inline Python script that prints snapshots repeatedly.
    This avoids needing a separate .py file on disk.
    """
    return (
        "import time\n"
        "from free_claude_code.core.monitoring.bottom import BottomMonitor\n"
        "m = BottomMonitor(); m.initialize()\n"
        "print('--- Bottom Monitor (BoHTOM) ---')\n"
        "while True:\n"
        "    snap = m.snapshot()\n"
        "    print('\\nSnapshot:', snap)\n"
        "    time.sleep(2)\n"
    )


def launch_bottom() -> str:
    """
    Launch the BottomMonitor viewer in a new terminal window.

    Returns a human-readable status string.
    """

    try:
        script = _viewer_script()

        # Write the viewer script to a temporary file
        import tempfile

        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix="_bottom_viewer.py",
            mode="w",
            encoding="utf-8",
        )
        tmp.write(script)
        tmp.close()

        path = tmp.name

        # Platform-specific terminal launching
        if sys.platform.startswith("win"):
            # Windows Terminal (wt.exe) if available
            try:
                subprocess.Popen(["wt.exe", "python", path])
                return "Launched bottom monitor in Windows Terminal"
            except Exception:
                # Fallback to cmd.exe
                subprocess.Popen(["cmd.exe", "/k", "python", path])
                return "Launched bottom monitor in cmd.exe"

        elif sys.platform.startswith("darwin"):
            # macOS Terminal
            subprocess.Popen(
                ["open", "-a", "Terminal", path]
            )
            return "Launched bottom monitor in macOS Terminal"

        else:
            # Linux / Unix
            # Try gnome-terminal, xterm, or fallback to direct execution
            for term in ("gnome-terminal", "xterm"):
                if shutil.which(term):
                    subprocess.Popen([term, "--", "python3", path])
                    return f"Launched bottom monitor in {term}"

            # Fallback: run in background
            subprocess.Popen(["python3", path])
            return "Launched bottom monitor (background mode)"

    except Exception as e:
        logger.error(f"Failed to launch bottom monitor: {e}")
        return f"Failed to launch bottom monitor: {e}"
