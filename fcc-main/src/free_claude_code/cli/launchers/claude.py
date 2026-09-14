from __future__ import annotations

# ============================================================
# FCC Claude Launcher — Repaired & Enhanced
# ============================================================

from typing import Any
import asyncio
import subprocess
import shutil

from loguru import logger

from free_claude_code.config.logging_config import ensure_logging_initialized_early
from free_claude_code.config.settings import Settings
from free_claude_code.runtime.bootstrap import build_asgi_app
from free_claude_code.runtime.provider_manager import ProviderRuntimeManager

# Initialize logging as early as possible
ensure_logging_initialized_early()

# ------------------------------------------------------------
# Windows Terminal + WSL selection logic
# ------------------------------------------------------------

WSL_DISTROS = {
    "1": "Ubuntu",        # Default + stable
    "2": "kali-linux",    # For 600-OSINT model
    "3": "Athena",        # Hardened environment
}

# Default working directory for Claude inside WSL
# Adjust if your FCC root moves.
CLAUDE_WORKDIR = "/mnt/c/Users/Administrator/Desktop/fcc/fcc-main"

# Pane mode: "V" = vertical, "H" = horizontal, None = new-tab
DEFAULT_PANE_MODE = "V"


def _wt_available() -> bool:
    """Check if Windows Terminal is available."""
    return shutil.which("wt.exe") is not None


def _spawn_wsl_pane(distro: str, pane_mode: str | None = DEFAULT_PANE_MODE) -> bool:
    """
    Spawn Claude inside a dedicated Windows Terminal pane running WSL.
    - One pane per Claude instance (thinker).
    - Claude runs in WSL, in CLAUDE_WORKDIR, via `fcc-claude`.
    """
    if not _wt_available():
        print("[FCC] Windows Terminal not available — running Claude in current shell.")
        return False

    # Build WT command: split-pane or new-tab
    wt_cmd: list[str] = ["wt.exe", "-w", "0"]

    if pane_mode in ("V", "H"):
        # Split pane vertically or horizontally
        wt_cmd += ["split-pane", f"-{pane_mode}"]
    else:
        # Fallback: new tab
        wt_cmd += ["new-tab"]

    wt_cmd += [
        "--title", f"Claude ({distro})",
        "--",  # Separator before the actual command
        "wsl.exe", "-d", distro,
        "bash", "-lc",
        f"cd {CLAUDE_WORKDIR} && fcc-claude"
    ]

    try:
        subprocess.Popen(wt_cmd)
        print(f"[FCC] Claude WSL pane launched ({distro}) via Windows Terminal.")
        logger.debug("Claude launcher: WT command = %r", wt_cmd)
        return True
    except Exception as exc:
        print(f"[FCC] Claude WSL pane failed safely: {exc}")
        logger.warning("Claude launcher: WT pane spawn failed: %s", exc)
        return False


# ------------------------------------------------------------
# Original FCC Claude runtime warmup (preserved)
# ------------------------------------------------------------

def _resolve_setting(obj: Any, name: str, default: Any) -> Any:
    """Return attribute `name` from obj if present, otherwise default."""
    return getattr(obj, name, default)


async def _warm_runtime(settings: Settings) -> None:
    """
    Initialize ProviderRuntimeManager and warm model cache.
    Claude does NOT start a server; warmup is optional but helpful.
    """
    manager = ProviderRuntimeManager(settings)
    logger.info(
        "Claude runtime: ProviderRuntimeManager initialized (generation_id=%s)",
        manager.current_generation_id,
    )

    try:
        result = await manager.warm_referenced_model_cache()
        logger.info(
            "Claude runtime: provider model cache warmed: refreshed_providers=%s errors=%s",
            result.refreshed_provider_ids,
            result.errors,
        )
    except Exception as exc:
        logger.warning(
            "Claude runtime warmup failed: exc_type=%s",
            type(exc).__name__,
        )


# ------------------------------------------------------------
# Enhanced Claude launcher
# ------------------------------------------------------------

def launch() -> None:
    print("[FCC] Launching Claude client runtime...")
    logger.debug("Claude launcher: constructing Settings and building ASGI client app.")

    # --------------------------------------------------------
    # WSL distro selection menu
    # --------------------------------------------------------
    print("\n[FCC] Select Linux environment for Claude:")
    print("  1) Ubuntu (default, stable)")
    print("  2) Kali (600-OSINT model)")
    print("  3) Athena (hardened)")

    choice = input("[FCC] Choose distro (1-3): ").strip()
    distro = WSL_DISTROS.get(choice, "Ubuntu")

    print(f"[FCC] Selected Linux environment: {distro}")

    # --------------------------------------------------------
    # Spawn Claude in WSL pane (preferred)
    # --------------------------------------------------------
    if _spawn_wsl_pane(distro, pane_mode=DEFAULT_PANE_MODE):
        print("[FCC] Claude launched in dedicated WSL pane. This shell will exit.")
        return

    # --------------------------------------------------------
    # Fallback: run Claude in current shell as client
    # --------------------------------------------------------
    settings = Settings()

    # Claude builds the ASGI client app but DOES NOT start uvicorn.
    app = build_asgi_app(settings)

    # Optional: warm provider runtime for Claude-side tools
    asyncio.run(_warm_runtime(settings))

    logger.info(
        "Claude client runtime initialized. Connect to FCC-server at %s:%s",
        settings.host,
        settings.port,
    )

    print("[FCC] Claude runtime ready. Use fcc-server to start the main server.")
    print("[FCC] Claude client connected to FCC-server for inference, agents, and providers.")


if __name__ == "__main__":
    launch()
