from loguru import logger
import os
import platform
import shutil
import subprocess
"""
Terminal Monitor Manager

Handles launching external terminal-based monitors:
- btop
- glances
- htop
- bottom (BoHTOM launcher)

Non-blocking, best-effort, and never critical to core/L1.
"""




def _working_monitor_executable(name: str) -> str | None:
    """Return a monitor executable only when its launcher can actually start.

    Windows entry-point executables embed the Python interpreter path used when
    they were installed. ``shutil.which`` alone therefore accepts stale shims
    (for example, one left behind after a Python version upgrade).
    """
    path = shutil.which(name)
    if path is None:
        return None
    try:
        result = subprocess.run(
            [path, "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=3,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        logger.warning("Monitor launcher is unusable: monitor={} path={}", name, path)
        return None
    if result.returncode != 0:
        logger.warning(
            "Monitor launcher exited unsuccessfully: monitor={} path={}", name, path
        )
        return None
    return path


# ============================================================
# ORIGINAL CLASS (kept exactly as-is)
# ============================================================


class TerminalMonitorManager:
    def __init__(self) -> None:
        # Detect external terminal tools
        self.available: dict[str, str] = {
            "btop": _working_monitor_executable("btop"),
            "glances": _working_monitor_executable("glances"),
            "htop": _working_monitor_executable("htop"),
            # bottom is NOT a system binary, so we mark it as "internal"
            # and handle it separately in launch()
            "bottom": "internal",
        }

    def status(self) -> dict[str, str]:
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

    def __init__(self, instance_id: str | None = None) -> None:
        super().__init__()
        self.instance_id = instance_id or "default"
        logger.info(
            f"[Monitor] EnhancedTerminalMonitorManager initialized (instance={self.instance_id})"
        )

    def _launch_external(self, name: str, path: str) -> dict[str, str]:
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

    def launch(self, name: str) -> dict[str, str]:
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
            logger.warning(
                f"[Monitor] {name} not installed (instance={self.instance_id})"
            )
            return {
                "monitor": name,
                "status": "missing",
                "instance": self.instance_id,
            }

        return self._launch_external(name, path)

    def launch_all(self) -> dict[str, dict[str, str]]:
        """Launch every known terminal monitor."""
        results = {}
        for name in self.available:
            results[name] = self.launch(name)
        return results

    def launch_defaults(self) -> dict[str, dict[str, str]]:
        """Launch btop plus explicitly requested additional terminal monitors.

        ``FCC_ADDITIONAL_TERMINAL_MONITORS`` accepts a comma-separated list of
        monitor names, such as ``glances,bottom``.  This keeps btop as the
        stable default while preserving an extensible monitor cluster.
        """
        configured = os.getenv("FCC_ADDITIONAL_TERMINAL_MONITORS", "")
        names = ["btop"]
        names.extend(name.strip().lower() for name in configured.split(",") if name.strip())

        results = {}
        for name in dict.fromkeys(names):
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
    manager.launch_defaults()
