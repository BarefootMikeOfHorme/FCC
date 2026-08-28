"""
Enhanced monitoring launcher for FCC.
Safe-to-fail external monitors + internal dashboard hook.
"""

import subprocess
import shutil

# Optional internal dashboard
try:
    from free_claude_code.core.monitoring_dashboard import start_monitoring_dashboard
except Exception:
    start_monitoring_dashboard = None


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


def launch_monitoring():
    """Launch monitoring dashboards (safe-to-fail combo)."""
    print("[FCC] Launching monitoring dashboards...")

    # Primary legacy monitor
    _try_launch(["btop"], "btop")

    # Combo monitors (safe-to-fail)
    _try_launch(["bottom"], "bottom")
    _try_launch(["htop"], "htop")
    _try_launch(["glances"], "glances")
    _try_launch(["nmon"], "nmon")
    _try_launch(["nom"], "nom")

    # Internal FCC dashboard
    if start_monitoring_dashboard:
        try:
            print("[FCC] Starting internal monitoring dashboard...")
            subprocess.Popen(["python", "-m", "free_claude_code.core.monitoring_dashboard"])
        except Exception as e:
            print(f"[FCC] Internal dashboard failed safely: {e}")
    else:
        print("[FCC] Internal dashboard not available — skipping.")
