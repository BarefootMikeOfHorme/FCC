"""Structured DEBUG traces for end-to-end request / CLI / provider logging.

Emitted lines are merged into JSON log rows by ``config.logging_config``.
Conversation and Claude Code prompts are logged verbatim unless values live under
sanitized credential keys (e.g. ``api_key``, ``authorization``). The default
INFO log level excludes these detailed request traces.

This module is FCC-core grade and backwards-compatible with existing usages:

- Preserves `TRACE_PAYLOAD_BINDING`.
- Preserves `sanitize_trace_value`.
- Preserves `trace_event` semantics, but now accepts both:
  - `trace_event(stage=..., event=..., source=..., ...)`
  - `trace_event("event-name", key=value, ...)` (simple form).
- Preserves `traced_async_stream`, `close_stream_input`,
  `extract_claude_session_id_from_headers`, `provider_chat_body_snapshot`.
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncGenerator, AsyncIterator, Callable, Mapping
from typing import Any, Optional, TypeVar

from loguru import logger

try:
    # Prefer local core import to avoid absolute package dependency.
    from .async_iterators import try_close_async_iterator  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    # Fallback: best-effort no-op close.
    async def try_close_async_iterator(iterator: object) -> BaseException | None:  # type: ignore[func-returns-value]
        return None


TRACE_PAYLOAD_BINDING = "trace_payload"

_SECRET_VALUE_KEYS = frozenset(
    k.lower()
    for k in (
        "authorization",
        "x-api-key",
        "anthropic-auth-token",
        "api_key",
        "password",
        "secret",
        "token",
        "bearer_token",
        "openapi_token",
        "nvidia-api-key",
    )
)

# Python 3.11+ BaseExceptionGroup; provide a fallback for older runtimes.
try:
    BaseExceptionGroup  # type: ignore[used-before-assignment]
except NameError:  # noqa: F821
    class BaseExceptionGroup(Exception):  # type: ignore[valid-type]
        """Fallback BaseExceptionGroup for pre-3.11 runtimes."""

        def __init__(self, message: str, exceptions: list[BaseException]) -> None:
            super().__init__(message)
            self.exceptions = exceptions


StreamValue = TypeVar("StreamValue")


def sanitize_trace_value(obj: Any) -> Any:
    """Recursively copy JSON-like structures redacting credential-shaped keys."""
    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            key_str = str(k)
            if key_str.lower() in _SECRET_VALUE_KEYS:
                out[key_str] = "<redacted>"
            else:
                out[key_str] = sanitize_trace_value(v)
        return out
    if isinstance(obj, (tuple, list)):
        return [sanitize_trace_value(x) for x in obj]
    return obj


def _build_trace_payload(
    *,
    stage: Optional[str],
    event: Optional[str],
    source: Optional[str],
    fields: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Internal helper to construct a sanitized trace payload."""
    payload = {
        "stage": stage,
        "event": event,
        "source": source,
        **fields,
    }
    return sanitize_trace_value(payload)


def trace_event(
    event: Optional[str] = None,
    *,
    stage: Optional[str] = None,
    source: Optional[str] = None,
    **fields: Any,
) -> None:
    """Emit one structured DEBUG trace row merged into JSON by the log sink.

    Backwards-compatible semantics:

    - Original form (still supported):
      `trace_event(stage="...", event="...", source="...", key=value, ...)`

    - New simple form (also supported):
      `trace_event("event-name", key=value, ...)`

    If `stage` or `source` are omitted, they default to `None` and can be
    interpreted by downstream logging/monitoring as generic traces.
    """
    # If called in the original keyword-only style, `event` will be provided
    # via the keyword argument. If called in the new simple style, `event`
    # is the positional argument.
    payload = _build_trace_payload(
        stage=stage,
        event=event,
        source=source,
        fields=fields,
    )
    logger.bind(**{TRACE_PAYLOAD_BINDING: payload}).debug("TRACE {}", event or "<event>")


async def close_stream_input(
    iterator: object,
    *,
    owner: str,
    source: str,
    preserved_error: BaseException | None,
) -> None:
    """Close one transform input and observe cleanup failure without raising it."""
    close_error = await try_close_async_iterator(iterator)
    if close_error is None:
        return
    trace_event(
        stage="lifecycle",
        event="stream.input.close_failed",
        source=source,
        owner=owner,
        close_exc_type=type(close_error).__name__,
        preserved_exc_type=(
            type(preserved_error).__name__ if preserved_error is not None else None
        ),
    )


def extract_claude_session_id_from_headers(headers: Mapping[str, str]) -> Optional[str]:
    """Best-effort session id forwarded by Claude Code / SDK via HTTP."""
    lowered = {str(k).lower(): v for k, v in headers.items() if isinstance(v, str)}
    for key in (
        "anthropic-session-id",
        "x-anthropic-session-id",
        "claude-session-id",
        "x-claude-session-id",
    ):
        candidate = lowered.get(key)
        if candidate:
            return candidate
    return None


async def traced_async_stream(
    agen: AsyncIterator[StreamValue],
    *,
    stage: str,
    source: str,
    complete_event: str,
    interrupted_event: str,
    chunk_event: Optional[str] = None,
    chunk_interval: int = 250,
    extra: Optional[Mapping[str, Any]] = None,
    item_size: Optional[Callable[[StreamValue], int]] = None,
) -> AsyncGenerator[StreamValue, None]:
    """Trace completion and interruption for one typed asynchronous stream.

    This function is backwards-compatible with the original signature, but
    now uses more defensive error handling and integrates with `trace_event`.
    """
    common = dict(extra or {})
    count = 0
    nbytes = 0
    interrupted = False

    try:
        async for chunk in agen:
            count += 1
            if item_size is not None:
                try:
                    nbytes += item_size(chunk)
                except Exception:  # noqa: BLE001
                    # Best-effort: ignore item_size failures.
                    pass
            else:
                if isinstance(chunk, str):
                    nbytes += len(chunk.encode("utf-8", errors="replace"))

            if chunk_event and chunk_interval > 0 and count % chunk_interval == 0:
                trace_event(
                    stage=stage,
                    event=chunk_event,
                    source=source,
                    stream_chunks_so_far=count,
                    stream_bytes_so_far=nbytes,
                    **common,
                )
            yield chunk
    except GeneratorExit:
        # Propagate generator close without tracing as an error.
        raise
    except asyncio.CancelledError:
        interrupted = True
        trace_event(
            stage=stage,
            event=interrupted_event,
            source=source,
            stream_chunks=count,
            stream_bytes=nbytes,
            outcome="cancelled",
            **common,
        )
        raise
    except BaseExceptionGroup as grp:
        interrupted = True
        trace_event(
            stage=stage,
            event=interrupted_event,
            source=source,
            stream_chunks=count,
            stream_bytes=nbytes,
            outcome="exception_group",
            note=str(grp),
            **common,
        )
        raise
    except Exception as exc:  # noqa: BLE001
        interrupted = True
        trace_event(
            stage=stage,
            event=interrupted_event,
            source=source,
            stream_chunks=count,
            stream_bytes=nbytes,
            outcome="error",
            exc_type=type(exc).__name__,
            **common,
        )
        raise
    finally:
        # sys.exception() is Python 3.11+; fall back gracefully if unavailable.
        preserved: BaseException | None
        try:
            preserved = sys.exception()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            preserved = None
        await close_stream_input(
            agen,
            owner="traced_async_stream",
            source=source,
            preserved_error=preserved,
        )

    if not interrupted:
        trace_event(
            stage=stage,
            event=complete_event,
            source=source,
            stream_chunks=count,
            stream_bytes=nbytes,
            outcome="ok",
            **common,
        )


def provider_chat_body_snapshot(body: Mapping[str, Any]) -> dict[str, Any]:
    """Sanitized OpenAI-compat chat body subset for traces (conversation text verbatim)."""
    keys = ("model", "messages", "tools", "tool_choice", "temperature", "max_tokens")
    snap = {k: body[k] for k in keys if k in body and body[k] is not None}
    return sanitize_trace_value(snap)
