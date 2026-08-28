"""
Track and clean up spawned CLI subprocesses.

Enhanced for monitoring orchestration:
- Added get_registered_pids() for shutdown coordination.
- Added kill_tagged_best_effort() for future monitor grouping.
"""

import atexit
import os
import signal
import subprocess
import threading

from loguru import logger

_lock = threading.Lock()
_pids: set[int] = set()
_pid_tags: dict[int, str] = {}  # NEW: optional tagging for monitor groups
_atexit_registered = False


def ensure_atexit_registered() -> None:
    global _atexit_registered
    with _lock:
        if _atexit_registered:
            return
        atexit.register(kill_all_best_effort)
        _atexit_registered = True


def register_pid(pid: int, tag: str | None = None) -> None:
    """Register a PID, optionally tagged (e.g., 'monitor', 'dashboard')."""
    if not pid:
        return
    ensure_atexit_registered()
    with _lock:
        _pids.add(int(pid))
        if tag:
            _pid_tags[int(pid)] = tag


def unregister_pid(pid: int) -> None:
    if not pid:
        return
    with _lock:
        _pids.discard(int(pid))
        _pid_tags.pop(int(pid), None)


def get_registered_pids() -> list[int]:
    """Return a snapshot of all tracked PIDs."""
    with _lock:
        return list(_pids)


def kill_pid_tree_best_effort(pid: int) -> None:
    """Kill a tracked process and its children where the platform supports it."""
    if not pid:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception as e:
            logger.debug("process_registry: taskkill failed pid=%s: %s", pid, e)
        return

    try:
        os.kill(pid, signal.SIGTERM)
    except Exception as e:
        logger.debug("process_registry: terminate failed pid=%s: %s", pid, e)


def kill_tagged_best_effort(tag: str) -> None:
    """Kill only processes with a specific tag (e.g., 'monitor')."""
    with _lock:
        tagged = [pid for pid, t in _pid_tags.items() if t == tag]

    for pid in tagged:
        kill_pid_tree_best_effort(pid)
        unregister_pid(pid)


def kill_all_best_effort() -> None:
    """Kill any still-running registered pids (best-effort)."""
    with _lock:
        pids = list(_pids)
        _pids.clear()
        _pid_tags.clear()

    for pid in pids:
        kill_pid_tree_best_effort(pid)
