from __future__ import annotations

from typing import Any
from loguru import logger
from free_claude_code.config.settings import Settings
from free_claude_code.runtime.bootstrap import build_asgi_app
import uvicorn


def _resolve_setting(obj: Any, name: str, default: Any) -> Any:
    """Return attribute `name` from obj if present, otherwise default."""
    return getattr(obj, name, default)


def launch() -> None:
    print("[FCC] Launching Claude runtime...")
    logger.debug("Launcher: constructing Settings and building ASGI app.")

    settings = Settings()
    app = build_asgi_app(settings)

    host = _resolve_setting(settings, "host", _resolve_setting(settings, "server_host", "127.0.0.1"))
    port = _resolve_setting(settings, "port", _resolve_setting(settings, "server_port", 8082))
    log_level = _resolve_setting(settings, "log_level", "info").lower()

    logger.info("Starting uvicorn on %s:%s (log_level=%s)", host, port, log_level)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
    )


if __name__ == "__main__":
    launch()
