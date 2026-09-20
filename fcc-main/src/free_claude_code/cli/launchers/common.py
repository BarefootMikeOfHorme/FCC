"""
Shared process helpers for installed client CLI launchers.
Enhanced with terminal spawn helpers for monitoring cluster.
"""

import os
import shutil
import subprocess
import sys
import time
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


def proxy_v1_url(env: Mapping[str, str]) -> str:
    """Resolve the proxy base URL for Anthropic-style clients."""
    base = env.get("ANTHROPIC_BASE_URL") or "http://127.0.0.1:8082"
    while base.endswith("/"):
        base = base[:-1]
    return base


def preflight_proxy(env: Mapping[str, str]) -> bool:
    """Perform a lightweight health check against the FCC proxy."""
    base = proxy_v1_url(env)
    url = f"{base}{PROXY_PREFLIGHT_PATH}"
    request = Request(url, method="GET")

    try:
        with open_local_request(
            request,
            timeout=PROXY_PREFLIGHT_TIMEOUT_SECONDS,
        ) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, OSError):
        return False


def spawn_terminal_tab(command: str, title: str = "FCC Monitor") -> None:
    """Spawn a Windows Terminal tab safely."""
    wt_path = shutil.which("wt.exe")

    if wt_path is None:
        print("[FCC] Windows Terminal not found; falling back to PowerShell window.")
        try:
            subprocess.Popen(
                ["powershell", "-NoExit", "-Command", command]
            )
        except Exception as e:
            print(f"[FCC] PowerShell spawn failed safely: {e}")
        return

    try:
        subprocess.Popen(
            [
                wt_path,
                "new-tab",
                "--title",
                title,
                "powershell",
                "-NoExit",
                "-Command",
                command,
            ]
        )
        print(f"[FCC] Terminal tab spawned: {title}")
    except Exception as e:
        print(f"[FCC] Terminal spawn failed safely: {e}")


def resolve_client_binary(env: Mapping[str, str], binary_name: str) -> str | None:
    """
    Resolve the path to a client binary (e.g., dsh, claude, opencode).

    Checks:
    1. Explicit override via FCC_CLIENT_BINARY or <NAME>_BINARY in env.
    2. PATH via shutil.which.
    Returns the resolved path or None if not found.
    """
    override = env.get("FCC_CLIENT_BINARY") or env.get(f"{binary_name.upper()}_BINARY")
    if override:
        return override

    return shutil.which(binary_name)
