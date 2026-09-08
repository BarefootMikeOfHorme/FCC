# ============================================================
# FCC Server Entrypoint — Corrected & Enhanced
# ============================================================

import asyncio
import threading
import uvicorn

# Core FCC imports
from free_claude_code.config.settings import Settings
from free_claude_code.runtime.bootstrap import build_asgi_app

# Monitoring + Orchestrator imports (corrected)
from free_claude_code.core.monitoring.terminal_monitors import start_monitoring
from free_claude_code.cli.monitoring_orchestrator import start_monitoring_orchestrator

# Admin UI + Warm Runtime helpers
from free_claude_code.cli.entrypoints_helpers import (
    _open_admin_ui,
    _warm_runtime,
)


def serve():
    """
    Start FCC server using new ASGI architecture.
    Enhanced for expanded logging, monitoring protocols,
    multi-instance orchestration, and provider warmup.
    """

    # ---------------------------------------------------------
    # 1. Early logging initialization (Patch 2 + expanded)
    # ---------------------------------------------------------
    from free_claude_code.config.logging_config import ensure_logging_initialized_early
    ensure_logging_initialized_early()
    print("[FCC] Logging initialized (expanded protocols ready).")

    # ---------------------------------------------------------
    # 2. Settings + ASGI app
    # ---------------------------------------------------------
    settings = Settings()
    asgi_app = build_asgi_app(settings)

    print("[FCC] Starting server...")

    # ---------------------------------------------------------
    # 3. Provider warmup (Patch 3)
    # ---------------------------------------------------------
    asyncio.run(_warm_runtime(settings))

    # ---------------------------------------------------------
    # 4. Expanded monitoring protocol initialization
    # ---------------------------------------------------------
    # Enhanced terminal monitoring cluster
    threading.Thread(target=start_monitoring, daemon=True).start()

    # New monitoring orchestrator
    if start_monitoring_orchestrator:
        threading.Thread(target=start_monitoring_orchestrator, daemon=True).start()
    else:
        print("[FCC] Monitoring orchestrator not available; skipping.")

    # ---------------------------------------------------------
    # 5. Agent orchestration hooks (for your multi-instance vision)
    # ---------------------------------------------------------
    try:
        from free_claude_code.runtime.agent_orchestrator import initialize_agent_system
        initialize_agent_system(settings)
        print("[FCC] Agent orchestration initialized.")
    except Exception:
        print("[FCC] Agent orchestration not available; skipping.")

    # ---------------------------------------------------------
    # 6. Multi-instance registry (future expansion)
    # ---------------------------------------------------------
    try:
        from free_claude_code.runtime.instance_registry import initialize_instance_registry
        initialize_instance_registry(settings)
        print("[FCC] Instance registry initialized.")
    except Exception:
        print("[FCC] Instance registry not available; skipping.")

    # ---------------------------------------------------------
    # 7. Admin UI auto-open
    # ---------------------------------------------------------
    threading.Thread(target=_open_admin_ui, daemon=True).start()

    # ---------------------------------------------------------
    # 8. Start uvicorn ASGI server
    # ---------------------------------------------------------
    uvicorn.run(
        asgi_app.app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )
