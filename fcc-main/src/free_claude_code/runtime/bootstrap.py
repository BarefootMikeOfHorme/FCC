"""Construct the production FCC ASGI application and its owned resources."""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Optional

from loguru import logger

from free_claude_code.api.app import create_app
from free_claude_code.api.ports import ApiServices
from free_claude_code.config.logging_config import configure_logging
from free_claude_code.config.paths import server_log_path
from free_claude_code.config.settings import Settings
from free_claude_code.messaging.transcription import TranscriptionService
from free_claude_code.messaging.voice import Transcriber
from free_claude_code.providers.admission import ProviderAdmissionController
from free_claude_code.providers.base import BaseProvider, ProviderConfig
from free_claude_code.providers.nvidia_nim.voice import NvidiaNimTranscriber
from free_claude_code.providers.openai_codex import (
    OpenAIAuthManager,
    OpenAICodexProvider,
)
from free_claude_code.providers.runtime import ProviderRuntime
from free_claude_code.providers.runtime.factory import create_provider

from .application import ApplicationRuntime, RestartCallback
from .asgi import RuntimeASGIApp
from .codex_catalog import CodexModelCatalogPublisher
from .provider_manager import ProviderRuntimeManager

ProviderManagerReadyHook = Callable[[ProviderRuntimeManager], None]
RuntimeInitializedHook = Callable[[ApplicationRuntime], None]
AsgiReadyHook = Callable[[RuntimeASGIApp], None]
BootstrapCompleteHook = Callable[[], None]

provider_manager_ready: Optional[ProviderManagerReadyHook]
runtime_initialized: Optional[RuntimeInitializedHook]
asgi_ready: Optional[AsgiReadyHook]
bootstrap_complete: Optional[BootstrapCompleteHook]
_monitoring_import_error: Optional[ImportError] = None

try:
    from free_claude_code.cli.monitoring_orchestrator import (
        asgi_ready,
        bootstrap_complete,
        provider_manager_ready,
        runtime_initialized,
    )
except ImportError as exc:
    provider_manager_ready = None
    runtime_initialized = None
    asgi_ready = None
    bootstrap_complete = None
    _monitoring_import_error = exc


def _run_hook(name: str, hook: Callable[..., None] | None, *args: object) -> None:
    """Run an optional monitoring hook without making startup unavailable."""
    if hook is None:
        return
    try:
        hook(*args)
    except Exception as exc:
        logger.warning(
            "Monitoring hook failed: hook={} exc_type={}",
            name,
            type(exc).__name__,
        )


def server_ready_marker() -> None:
    """Log that the server runtime is initialized and ready."""
    logger.info("Server runtime initialized and ready to accept requests")


def _create_openai_provider(
    config: ProviderConfig,
    _settings: Settings,
    admission: ProviderAdmissionController,
    *,
    auth: OpenAIAuthManager,
) -> BaseProvider:
    """Factory for the OpenAI Codex provider."""
    return OpenAICodexProvider(config, auth=auth, admission=admission)


def _required_voice_key(api_key: str | None) -> str:
    """Ensure a required voice API key is present."""
    if not api_key:
        raise AssertionError("NIM voice settings were not validated")
    return api_key


def _create_transcriber(settings: Settings) -> Transcriber | None:
    """Create a transcriber instance based on settings, or None if disabled."""
    if not settings.voice_note_enabled:
        return None

    if settings.whisper_device == "nvidia_nim":
        return NvidiaNimTranscriber(
            model=settings.whisper_model,
            api_key=_required_voice_key(settings.nvidia_nim_api_key),
        )

    return TranscriptionService(
        model=settings.whisper_model,
        device=settings.whisper_device,
        huggingface_api_key=settings.huggingface_api_key,
    )


def build_asgi_app(
    settings: Settings,
    restart_callback: RestartCallback | None = None,
) -> RuntimeASGIApp:
    """Construct the complete server application and its resource owner."""
    log_path = Path(os.getenv("LOG_FILE") or server_log_path())
    configure_logging(
        log_path,
        level=settings.log_level,
        verbose_third_party=settings.log_raw_api_payloads,
    )

    if _monitoring_import_error is not None:
        logger.warning(
            "Monitoring hooks are unavailable: exc_type={}",
            type(_monitoring_import_error).__name__,
        )

    openai_auth = OpenAIAuthManager(proxy=settings.openai_proxy)
    openai_factory = partial(_create_openai_provider, auth=openai_auth)

    provider_constructor = partial(
        create_provider,
        injected_factories={"openai": openai_factory},
    )

    runtime_factory = partial(
        ProviderRuntime,
        provider_constructor=provider_constructor,
    )

    provider_manager = ProviderRuntimeManager(
        settings,
        runtime_factory=runtime_factory,
        connected_provider_ids=openai_auth.connected_provider_ids,
        model_catalog_publisher=CodexModelCatalogPublisher(),
    )

    _run_hook("provider_manager_ready", provider_manager_ready, provider_manager)

    runtime = ApplicationRuntime(
        provider_manager,
        transcriber=_create_transcriber(settings),
        restart_callback=restart_callback,
        connected_accounts={"openai": openai_auth},
    )

    _run_hook("runtime_initialized", runtime_initialized, runtime)

    services = ApiServices(
        requests=provider_manager,
        admin=runtime,
        tasks=runtime,
    )

    def on_started() -> None:
        server_ready_marker()
        _run_hook("bootstrap_complete", bootstrap_complete)

    asgi_app = RuntimeASGIApp(
        create_app(services),
        runtime,
        on_started=on_started,
    )

    _run_hook("asgi_ready", asgi_ready, asgi_app)
    return asgi_app
