"""
FCC server entrypoint for the new architecture.
Includes admin auto-open + monitoring initialization + orchestrator hook.
"""

import uvicorn
import webbrowser
import threading
import time

from free_claude_code.config.settings import Settings
from free_claude_code.runtime.bootstrap import build_asgi_app

# Monitoring launcher (legacy)
try:
    from free_claude_code.cli.monitoring import launch_monitoring_attached_to_server
except Exception:
    launch_monitoring_attached_to_server = None

# Monitoring orchestrator (new)
try:
    from free_claude_code.cli.monitoring_orchestrator import start_monitoring_orchestrator
except Exception:
    start_monitoring_orchestrator = None


def _open_admin_ui():
    """Open Admin UI shortly after server starts."""
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:8082/admin")


def _start_monitoring():
    """Start legacy monitoring attached to the server terminal."""
    if launch_monitoring_attached_to_server:
        launch_monitoring_attached_to_server("windows")
    else:
        print("[FCC] Legacy monitoring module not found; skipping.")


def serve():
    """
    Start FCC server using new ASGI architecture.
    Admin UI auto-opens.
    Monitoring starts after initialization.
    Orchestrator coordinates terminal + dashboard popouts.
    """
    settings = Settings()
    asgi_app = build_asgi_app(settings)

    print("[FCC] Starting server...")

    # Admin UI opener
    threading.Thread(target=_open_admin_ui, daemon=True).start()

    # Legacy monitoring initializer
    threading.Thread(target=_start_monitoring, daemon=True).start()

    # New monitoring orchestrator
    if start_monitoring_orchestrator:
        threading.Thread(target=start_monitoring_orchestrator, daemon=True).start()
    else:
        print("[FCC] Monitoring orchestrator not available; skipping.")

    # Start uvicorn ASGI server
    uvicorn.run(
        asgi_app.app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )
