"""Free Claude Code — Core Package

This package exposes the public core interfaces:

- Reasoning policies
- Async iterator lifecycle helpers
- JSON type vocabulary
- Logging integration
- Dependency resolver entrypoint
- Token estimation helpers
- Trace utilities
- Package version metadata

All heavy implementations live in their respective modules.
This file only re-exports stable public symbols and is intentionally lightweight.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Reasoning subsystem
# ---------------------------------------------------------------------------

from .reasoning import (
    DEFAULT_REASONING_POLICY,
    ReasoningControl,
    ReasoningEffort,
    ReasoningPolicy,
)

__all__ = [
    "DEFAULT_REASONING_POLICY",
    "ReasoningControl",
    "ReasoningEffort",
    "ReasoningPolicy",
]

# ---------------------------------------------------------------------------
# Async iterator lifecycle helpers
# ---------------------------------------------------------------------------

from .async_iterators import (
    AsyncCloseable,
    try_close_async_iterator,
    close_all_async,
    safe_async_context,
    exhaust_async_iterator,
    exhaust_and_close,
    cancel_and_close,
)

__all__ += [
    "AsyncCloseable",
    "try_close_async_iterator",
    "close_all_async",
    "safe_async_context",
    "exhaust_async_iterator",
    "exhaust_and_close",
    "cancel_and_close",
]

# ---------------------------------------------------------------------------
# JSON vocabulary
# ---------------------------------------------------------------------------

from .json_types import (
    JsonScalar,
    JsonPrimitive,
    JsonValue,
    JsonArray,
    JsonDict,
    JsonObject,
    JsonSerializable,
    JsonError,
    ensure_json_safe,
    json_dump,
    json_load,
    load_any,
    dump_any,
    as_json_dict,
    as_json_array,
)

__all__ += [
    "JsonScalar",
    "JsonPrimitive",
    "JsonValue",
    "JsonArray",
    "JsonDict",
    "JsonObject",
    "JsonSerializable",
    "JsonError",
    "ensure_json_safe",
    "json_dump",
    "json_load",
    "load_any",
    "dump_any",
    "as_json_dict",
    "as_json_array",
]

# ---------------------------------------------------------------------------
# Logging integration
# ---------------------------------------------------------------------------

from .logging_integration import (
    setup_rich_logging,
    get_rich_logger,
    log_with_request_id,
    log_with_session_id,
    log_with_context,
)

__all__ += [
    "setup_rich_logging",
    "get_rich_logger",
    "log_with_request_id",
    "log_with_session_id",
    "log_with_context",
]

# ---------------------------------------------------------------------------
# Dependency resolver
# ---------------------------------------------------------------------------

from .dependency_resolver import resolve_dependencies

__all__ += [
    "resolve_dependencies",
]

# ---------------------------------------------------------------------------
# Token estimation helpers
# ---------------------------------------------------------------------------

try:
    from .token_estimation import (
        estimate_text_tokens,
        estimate_text_tokens_for_model,
        estimate_batch_tokens,
        estimate_batch_tokens_for_model,
        estimate_stream_tokens,
        estimate_stream_tokens_for_model,
    )
except Exception:  # noqa: BLE001
    # Optional module; keep core import surface safe-to-fail.
    def estimate_text_tokens(text: str) -> int:  # type: ignore[func-returns-value]
        return max(1, len(text) // 4) if text else 0

    def estimate_text_tokens_for_model(text: str, model_id: str | None) -> int:  # type: ignore[func-returns-value]
        return estimate_text_tokens(text)

    def estimate_batch_tokens(texts: list[str]) -> int:  # type: ignore[func-returns-value]
        return sum(estimate_text_tokens(t) for t in texts)

    def estimate_batch_tokens_for_model(texts: list[str], model_id: str | None) -> int:  # type: ignore[func-returns-value]
        return sum(estimate_text_tokens_for_model(t, model_id) for t in texts)

    def estimate_stream_tokens(chunks: list[str]) -> int:  # type: ignore[func-returns-value]
        return sum(estimate_text_tokens(c) for c in chunks)

    def estimate_stream_tokens_for_model(chunks: list[str], model_id: str | None) -> int:  # type: ignore[func-returns-value]
        return sum(estimate_text_tokens_for_model(c, model_id) for c in chunks)

__all__ += [
    "estimate_text_tokens",
    "estimate_text_tokens_for_model",
    "estimate_batch_tokens",
    "estimate_batch_tokens_for_model",
    "estimate_stream_tokens",
    "estimate_stream_tokens_for_model",
]

# ---------------------------------------------------------------------------
# Trace utilities
# ---------------------------------------------------------------------------

try:
    from .trace import (
        sanitize_trace_value,
        trace_event,
        traced_async_stream,
        close_stream_input,
        extract_claude_session_id_from_headers,
        provider_chat_body_snapshot,
        TRACE_PAYLOAD_BINDING,
    )
except Exception:  # noqa: BLE001
    # Optional module; provide minimal no-op fallbacks.
    TRACE_PAYLOAD_BINDING = "trace_payload"

    def sanitize_trace_value(obj: object) -> object:  # type: ignore[func-returns-value]
        return obj

    def trace_event(event: str, **fields: object) -> None:  # type: ignore[func-returns-value]
        return

    async def traced_async_stream(  # type: ignore[func-returns-value]
        agen,
        *,
        stage: str,
        source: str,
        complete_event: str,
        interrupted_event: str,
        chunk_event: str | None = None,
        chunk_interval: int = 250,
        extra: dict[str, object] | None = None,
        item_size=None,
    ):
        async for chunk in agen:
            yield chunk

    async def close_stream_input(  # type: ignore[func-returns-value]
        iterator: object,
        *,
        owner: str,
        source: str,
        preserved_error: BaseException | None,
    ) -> None:
        return

    def extract_claude_session_id_from_headers(headers: dict[str, str]) -> str | None:  # type: ignore[func-returns-value]
        return None

    def provider_chat_body_snapshot(body: dict[str, object]) -> dict[str, object]:  # type: ignore[func-returns-value]
        return body

__all__ += [
    "TRACE_PAYLOAD_BINDING",
    "sanitize_trace_value",
    "trace_event",
    "traced_async_stream",
    "close_stream_input",
    "extract_claude_session_id_from_headers",
    "provider_chat_body_snapshot",
]

# ---------------------------------------------------------------------------
# Package metadata
# ---------------------------------------------------------------------------

try:
    from .version import package_version  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    def package_version() -> str:  # type: ignore[func-returns-value]
        return "0+unknown"

__version__ = package_version()
__all__ += ["__version__", "package_version"]
