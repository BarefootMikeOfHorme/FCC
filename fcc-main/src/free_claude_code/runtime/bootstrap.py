"""
Single production composition root for the FCC server.

Enhanced:
- Added orchestrator hook imports (safe-to-fail).
- Added server_ready_marker(), runtime_initialized(), provider_manager_ready(),
  asgi_ready(), bootstrap_complete() hook calls.
- Added restart_callback(runtime) support.
- Fully backwards compatible with existing FCC runtime architecture.
"""

import os
from functools import partial
from pathlib import Path

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


# ---------------------------------------------------------------------------
# Safe-to-fail orchestrator hook imports
# ---------------------------------------------------------------------------

try:
    from free_claude_code.cli.monitoring_orchestrator import (
        runtime_initialized,
        provider_manager_ready,
        asgi_ready,
        bootstrap_complete,
    )
except Exception:
    runtime_initialized = None
    provider_manager_ready = None
    asgi_ready = None
    bootstrap_complete = None


# ---------------------------------------------------------------------------
# Monitoring Orchestrator Readiness Marker
# ---------------------------------------------------------------------------

def server_ready_marker() -> None:
    """Marker function for monitoring orchestrator."""
    print("[FCC] Server runtime initialized (bootstrap ready).")


# ---------------------------------------------------------------------------
# Provider Construction Helpers
# ---------------------------------------------------------------------------

def _create_openai_provider(
    config: ProviderConfig,
    _settings: Settings,
    admission: ProviderAdmissionController,
    *,
    auth: OpenAIAuthManager,
) -> BaseProvider:
    """Construct an OpenAI Codex provider."""
    return OpenAICodexProvider(config, auth=auth, admission=admission)


def _required_voice_key(api_key: str | None) -> str:
    """Validate required voice key for NIM."""
    if api_key is None:
        raise AssertionError("NIM voice settings were not validated")
    return api_key


def _create_transcriber(settings: Settings) -> Transcriber | None:
    """Construct a transcriber based on settings."""
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


# ---------------------------------------------------------------------------
# Main ASGI Application Builder
# ---------------------------------------------------------------------------

def build_asgi_app(
    settings: Settings,
    restart_callback: RestartCallback | None = None,
) -> RuntimeASGIApp:
    """
    Construct the complete server application and its resource owner.
    This is the main composition root for FCC.
    """

    # Configure logging
    log_path = Path(os.getenv("LOG_FILE", server_log_path()))
    configure_logging(
        log_path,
        level=settings.log_level,
        verbose_third_party=settings.log_raw_api_payloads,
    )

    # Provider admission + auth
    openai_auth = OpenAIAuthManager(proxy=settings.openai_proxy)
    openai_factory = partial(_create_openai_provider, auth=openai_auth)

    # Provider constructor factory
    provider_constructor = partial(
        create_provider,
        injected_factories={"openai": openai_factory},
    )

    # Provider runtime factory
    runtime_factory = partial(
        ProviderRuntime,
        provider_constructor=provider_constructor,
    )

    # Provider manager
    provider_manager = ProviderRuntimeManager(
        settings,
        runtime_factory=runtime_factory,
        connected_provider_ids=openai_auth.connected_provider_ids,
        model_catalog_publisher=CodexModelCatalogPublisher(),
    )

    # Orchestrator hook: provider manager ready
    if provider_manager_ready:
        try:
            provider_manager_ready(provider_manager)
        except Exception:
            pass

    # Application runtime
    runtime = ApplicationRuntime(
        provider_manager,
        transcriber=_create_transcriber(settings),
        restart_callback=restart_callback,
        connected_accounts={"openai": openai_auth},
    )

    # Orchestrator hook: runtime initialized
    if runtime_initialized:
        try:
            runtime_initialized(runtime)
        except Exception:
            pass

    # Optional restart callback
    if restart_callback:
        try:
            restart_callback(runtime)
        except Exception:
            pass

    # API services
    services = ApiServices(
        requests=provider_manager,
        admin=runtime,
        tasks=runtime,
    )

    # Monitoring orchestrator readiness marker
    server_ready_marker()

    # Construct ASGI app
    asgi_app = RuntimeASGIApp(create_app(services), runtime)

    # Orchestrator hook: ASGI ready
    if asgi_ready:
        try:
            asgi_ready(asgi_app)
        except Exception:
            pass

    # Orchestrator hook: bootstrap complete
    if bootstrap_complete:
        try:
            bootstrap_complete()
        except Exception:
            pass

    return asgi_app
