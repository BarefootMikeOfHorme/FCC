import subprocess
import shutil
from typing import List

# Optional: internal FCC dashboard (safe import)
try:
    from .monitoring_dashboard import start_monitoring_dashboard
except Exception:
    start_monitoring_dashboard = None


def _try_launch(cmd: List[str], name: str) -> None:
    """Attempt to launch a monitor safely without crashing FCC."""
    try:
        if shutil.which(cmd[0]):
            print(f"[FCC] Launching {name}...")
            subprocess.Popen(cmd)
        else:
            print(f"[FCC] {name} not installed — skipping.")
    except Exception as e:
        print(f"[FCC] {name} failed to launch safely: {e}")


def launch_monitoring() -> None:
    """Launch monitoring dashboards (safe-to-fail combo).

    Existing behavior:
        - btop still launches as the primary monitor.

    Enhanced behavior:
        - bottom, htop, glances, nmon, nom are attempted but safe-to-fail.
        - Internal FCC Rich dashboard is started if available.
    """
    print("[FCC] Launching monitoring dashboards...")

    # --- PRIMARY / LEGACY MONITOR (unchanged behavior) ---
    _try_launch(["btop"], "btop")

    # --- COMBO MONITORS (safe-to-fail, optional) ---
    _try_launch(["bottom"], "bottom")
    _try_launch(["htop"], "htop")
    _try_launch(["glances"], "glances")
    _try_launch(["nmon"], "nmon")
    _try_launch(["nom"], "nom")

    # --- INTERNAL FCC DASHBOARD (Rich TUI) ---
    if start_monitoring_dashboard is not None:
        try:
            print("[FCC] Starting internal monitoring dashboard...")
            # Run in a separate process so it has its own terminal
            subprocess.Popen(
                ["python", "-m", "free_claude_code.core.monitoring_dashboard"],
            )
        except Exception as e:
            print(f"[FCC] Internal monitoring dashboard failed to start safely: {e}")
    else:
        print("[FCC] Internal monitoring dashboard not available — skipping.")
