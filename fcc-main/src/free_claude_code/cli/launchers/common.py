"""
Shared process helpers for installed client CLI launchers.
Enhanced with terminal spawn helpers for monitoring cluster.
"""

import shutil
import subprocess
import sys
from collections.abc import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request

from free_claude_code.cli.local_http import open_local_request
from free_claude_code.cli.process_registry import (
    kill_pid_tree_best_effort,
    register_pid,
    unregister_pid,
)

PROXY_PREFLIGHT_PATH = "/health"
PROXY_PREFLIGHT_TIMEOUT_SECONDS = 1.5


def spawn_terminal_tab(command: str, title: str = "FCC Monitor"):
    """Spawn a Windows Terminal tab safely."""
    try:
        subprocess.Popen([
            "wt.exe",
            "new-tab",
            "--title", title,
            "powershell",
            "-NoExit",
            "-Command", command
        ])
        print(f"[FCC] Terminal tab spawned: {title}")
    except Exception as e:
        print(f"[FCC] Terminal spawn failed safely: {e}")


# (rest of your original file unchanged)
