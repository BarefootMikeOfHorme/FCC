"""
FCC Server Lifecycle Supervisor (commands.py)

Coordinates:
- FastAPI/ASGI server startup and shutdown
- Config-driven restarts
- Admin UI auto-open
- Runtime health preflight checks
- Graceful shutdown and cleanup

Architectural Guarantees:
- Self-contained:
    All lifecycle logic is fully encapsulated here. No external dependencies
    on L1 internals, protocol engines, or UI layers.

- L1-compatible but L1-agnostic:
    The supervisor exposes stable, predictable behavior usable by L1 schedulers,
    protocol engines, or any higher-level automation — without depending on
    L1-specific structures, message formats, or runtime assumptions.

- Safe to call from CLI, Admin UI, or protocol engines:
    All operations are exception-safe, fire-and-forget, and designed so that
    server lifecycle failures never propagate upward or disrupt core system behavior.

This module hosts the runtime environment in which the Monitoring Orchestrator
executes, and therefore shares the same architectural guarantees.
"""

import threading
import time
import webbrowser
from enum import StrEnum

import uvicorn

from free_claude_code.cli.launchers.common import preflight_proxy
from free_claude_code.cli.process_registry import kill_all_best_effort
from free_claude_code.config.loader import clear_settings_cache, get_settings
from free_claude_code.config.server_urls import local_admin_url, local_proxy_root_url
from free_claude_code.config.settings import Settings
from free_claude_code.runtime.bootstrap import build_asgi_app

SERVER_GRACEFUL_SHUTDOWN_SECONDS = 5


def serve() -> None:
    """Start and supervise the FastAPI server."""
    ServerSupervisor().run()


class ServerStatus(StrEnum):
    """Observable state of the server owned by a supervisor."""

    STARTING = "Starting"
    RUNNING = "Running"
    STOPPING = "Stopping"
    STOPPED = "Stopped"


class ServerSupervisor:
    """
    Owns one FCC server lifecycle.

    Responsibilities:
    - Start and supervise the FastAPI/ASGI server
    - Apply config-driven restarts
    - Manage graceful shutdown
    - Coordinate Admin UI auto-open
    - Provide observable server status

    Architectural Guarantees:
    - Self-contained: all lifecycle logic lives here.
    - L1-compatible: callable from L1 schedulers or protocol engines.
    - L1-agnostic: does not depend on L1 internals or message formats.
    - Safe for CLI/Admin UI: fire-and-forget, exception-safe operations.
    """

    def __init__(self, *, console_logging: bool = True) -> None:
        self._console_logging = console_logging
        self._lock = threading.Lock()
        self._server: uvicorn.Server | None = None
        self._run_scheduled = False
        self._running = False
        self._stop_requested = False
        self._restart_generation = 0

    @property
    def status(self) -> ServerStatus:
        with self._lock:
            if self._run_scheduled:
                return ServerStatus.STARTING
            if not self._running:
                return ServerStatus.STOPPED
            if self._server is None:
                return ServerStatus.STARTING
            if self._server.should_exit:
                return ServerStatus.STOPPING
            if self._server.started:
                return ServerStatus.RUNNING
            return ServerStatus.STARTING

    def schedule_run(self) -> bool:
        """Reserve a worker run before its thread starts."""

        with self._lock:
            if self._stop_requested or self._run_scheduled or self._running:
                return False
            self._run_scheduled = True
            return True

    def run(self, *, open_admin_browser: bool | None = None) -> None:
        """Block until stopped, applying only fully closed Admin restarts."""

        with self._lock:
            self._run_scheduled = False
            if self._running:
                raise RuntimeError("The FCC server supervisor is already running.")
            if self._stop_requested:
                return
            self._running = True

        opened_admin_browser = False
        try:
            try:
                while not self._is_stop_requested():
                    with self._lock:
                        restart_generation = self._restart_generation
                    settings = load_server_settings()
                    should_open_admin = (
                        settings.open_admin_browser
                        if open_admin_browser is None
                        else open_admin_browser
                    ) and not opened_admin_browser
                    if not self._run_once(
                        settings,
                        open_admin_browser=should_open_admin,
                        restart_generation=restart_generation,
                    ):
                        return
                    opened_admin_browser = opened_admin_browser or should_open_admin
                    clear_settings_cache()
            except KeyboardInterrupt:
                return
        finally:
            with self._lock:
                self._server = None
                self._running = False
            kill_all_best_effort()

    def request_restart(self) -> bool:
        """Reload an active generation or coalesce into a scheduled fresh run."""

        with self._lock:
            if self._stop_requested:
                return False
            if self._run_scheduled:
                self._restart_generation += 1
                return True
            if not self._running:
                return False
            self._restart_generation += 1
            if self._server is not None:
                self._server.should_exit = True
            return True

    def request_stop(self) -> None:
        """Permanently stop this supervisor after graceful runtime cleanup."""

        with self._lock:
            self._stop_requested = True
            self._run_scheduled = False
            if self._server is not None:
                self._server.should_exit = True

    def _is_stop_requested(self) -> bool:
        with self._lock:
            return self._stop_requested

    def _run_once(
        self,
        settings: Settings,
        *,
        open_admin_browser: bool,
        restart_generation: int,
    ) -> bool:
        asgi_app = build_asgi_app(
            settings,
            restart_callback=self._request_runtime_restart,
        )
        config = uvicorn.Config(
            asgi_app,
            host=settings.host,
            port=settings.port,
            log_level="debug",
            log_config=(
                uvicorn.config.LOGGING_CONFIG if self._console_logging else None
            ),
            timeout_graceful_shutdown=SERVER_GRACEFUL_SHUTDOWN_SECONDS,
        )
        server = uvicorn.Server(config)
        with self._lock:
            self._server = server
            if self._stop_requested or self._restart_generation != restart_generation:
                server.should_exit = True

        if open_admin_browser:
            schedule_open_admin_browser(settings)
        server.run()

        with self._lock:
            if self._server is server:
                self._server = None
            restart_requested = self._restart_generation != restart_generation
            stop_requested = self._stop_requested
        return restart_requested and not stop_requested and asgi_app.runtime.is_closed

    def _request_runtime_restart(self) -> None:
        self.request_restart()


def load_server_settings() -> Settings:
    """Return the canonical cached settings."""
    return get_settings()


def open_admin_when_ready(settings: Settings) -> bool:
    """Wait briefly for /health, then open the current Admin UI."""
    admin_url = local_admin_url(settings)
    proxy_root_url = local_proxy_root_url(settings)
    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        if preflight_proxy(proxy_root_url) is None:
            return webbrowser.open(admin_url)
        time.sleep(0.15)
    return False


def schedule_open_admin_browser(settings: Settings) -> None:
    """Open Admin after health succeeds without blocking the caller."""
    threading.Thread(
        target=open_admin_when_ready,
        args=(settings,),
        name="fcc-open-admin-browser",
        daemon=True,
    ).start()
