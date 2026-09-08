"""
Enhanced monitoring launcher for FCC.
Safe-to-fail external monitors + internal dashboard hook.
Now supports Windows Terminal tab spawning for FCC-server monitoring cluster.
"""

import subprocess
import shutil
import sys
import os

# Optional internal dashboard
try:
    from free_claude_code.core.monitoring_dashboard import start_monitoring_dashboard
except Exception:
    start_monitoring_dashboard = None


# ------------------------------------------------------------
# Windows Terminal detection
# ------------------------------------------------------------

def _wt_available() -> bool:
    """Check if Windows Terminal (wt.exe) is available."""
    return shutil.which("wt.exe") is not None


def _spawn_wt_tab(title: str, command: str):
    """
    Spawn a new Windows Terminal tab attached to the same window.
    Safe-to-fail: falls back to subprocess.Popen if wt.exe is missing.
    """
    if _wt_available():
        try:
            subprocess.Popen([
                "wt.exe",
                "--window", "0",
                "--title", title,
                "--command", command
            ])
            print(f"[FCC] WT tab launched: {title}")
            return
        except Exception as e:
            print(f"[FCC] WT tab failed safely ({title}): {e}")

    # Fallback: normal subprocess
    try:
        subprocess.Popen(command.split())
        print(f"[FCC] Fallback launch: {title}")
    except Exception as e:
        print(f"[FCC] Fallback failed safely ({title}): {e}")


# ------------------------------------------------------------
# Original safe launcher (preserved exactly)
# ------------------------------------------------------------

def _try_launch(cmd, name):
    """Launch a monitor safely without crashing FCC."""
    try:
        if shutil.which(cmd[0]):
            print(f"[FCC] Launching {name}...")
            subprocess.Popen(cmd)
        else:
            print(f"[FCC] {name} not installed — skipping.")
    except Exception as e:
        print(f"[FCC] {name} failed safely: {e}")


# ------------------------------------------------------------
# Enhanced cluster launcher
# ------------------------------------------------------------

def launch_monitoring():
    """
    Launch monitoring dashboards (safe-to-fail combo).
    Enhanced to spawn monitors in Windows Terminal tabs when available.
    """

    print("[FCC] Launching monitoring dashboards...")

    # --------------------------------------------------------
    # FCC-server monitoring cluster (Windows Terminal tabs)
    # --------------------------------------------------------

    # Tab 2 → btop
    _spawn_wt_tab("btop", "btop")

    # Tab 3 → glances
    _spawn_wt_tab("glances", "glances")

    # Tab 4 → bottom
    _spawn_wt_tab("bottom", "bottom")

    # Tab 5 → BoHTOM placeholder (future custom bottom)
    # This will be replaced later when BoHTOM is implemented.
    _spawn_wt_tab("BoHTOM (placeholder)", "bottom")

    # --------------------------------------------------------
    # Legacy fallback monitors (preserved)
    # --------------------------------------------------------

    _try_launch(["htop"], "htop")
    _try_launch(["nmon"], "nmon")
    _try_launch(["nom"], "nom")

    # --------------------------------------------------------
    # Internal FCC dashboard (preserved)
    # --------------------------------------------------------

    if start_monitoring_dashboard:
        try:
            print("[FCC] Starting internal monitoring dashboard...")
            subprocess.Popen(["python", "-m", "free_claude_code.core.monitoring_dashboard"])
        except Exception as e:
            print(f"[FCC] Internal dashboard failed safely: {e}")
    else:
        print("[FCC] Internal dashboard not available — skipping.")
