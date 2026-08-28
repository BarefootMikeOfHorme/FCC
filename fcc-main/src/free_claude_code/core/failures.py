"""Protocol-neutral execution failure semantics for Free Claude Code.

This enhanced FCC-grade module provides:

- Backwards-compatible `ExecutionFailure` and `FailureKind`.
- Provider-neutral failure taxonomy.
- Rich metadata fields (provider, model, request_id, upstream details).
- Safe-to-fail normalization helpers for HTTP, SDK, and provider errors.
- ExceptionGroup-compatible extraction (Python 3.11+ and fallback).
- Structured logging and trace integration (best-effort).
- Convenience constructors for common failure patterns.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass
from enum import StrEnum
from typing import Any, Mapping, Optional

# ---------------------------------------------------------------------------
# FCC core integrations (best-effort)
# ---------------------------------------------------------------------------

try:
    from .logging_integration import log_with_context  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    def log_with_context(message: str, level: str = "info", **ctx: object) -> None:  # type: ignore[func-returns-value]
        return

try:
    from .trace import trace_event  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    def trace_event(event: str, **fields: object) -> None:  # type: ignore[func-returns-value]
        return

# Python 3.11 BaseExceptionGroup fallback
try:
    BaseExceptionGroup  # type: ignore[used-before-assignment]
except NameError:  # noqa: F821
    class BaseExceptionGroup(Exception):  # type: ignore[valid-type]
        """Fallback BaseExceptionGroup for pre-3.11 runtimes."""

        def __init__(self, message: str, exceptions: list[BaseException]) -> None:
            super().__init__(message)
            self.exceptions = exceptions


# ---------------------------------------------------------------------------
# Failure taxonomy
# ---------------------------------------------------------------------------

class FailureKind(StrEnum):
    """Stable failure categories shared across execution and wire adapters."""

    INVALID_REQUEST = "invalid_request"
    CONTEXT_WINDOW_EXCEEDED = "context_window_exceeded"
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RATE_LIMIT = "rate_limit"
    OVERLOADED = "overloaded"
    TIMEOUT = "timeout"
    UPSTREAM = "upstream"
    UNAVAILABLE = "unavailable"


# ---------------------------------------------------------------------------
# ExecutionFailure (FCC-grade)
# ---------------------------------------------------------------------------

@dataclass(slots=True, eq=False)
class ExecutionFailure(Exception):
    """A finalized provider-execution failure independent of any wire protocol.

    Fields:
        kind: FailureKind — canonical FCC failure category.
        status_code: int — HTTP or provider status code.
        message: str — human-readable message.
        retryable: bool — whether retry is safe.
        provider: Optional[str] — provider name (openai, anthropic, deepseek, etc.)
        model: Optional[str] — model ID involved.
        request_id: Optional[str] — provider request ID.
        upstream: Optional[Mapping[str, Any]] — raw upstream error details.
    """

    kind: FailureKind
    status_code: int
    message: str
    retryable: bool
    provider: Optional[str] = None
    model: Optional[str] = None
    request_id: Optional[str] = None
    upstream: Optional[Mapping[str, Any]] = None

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)

    def __setattr__(self, name: str, value: object) -> None:
        # Exception machinery must be able to update __traceback__, __cause__,
        # and __context__ while semantic failure fields remain immutable.
        if name in self.__slots__ and hasattr(self, name):
            raise FrozenInstanceError(f"cannot assign to field {name!r}")
        super().__setattr__(name, value)


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def find_execution_failure(exc: BaseException) -> ExecutionFailure | None:
    """Return the first canonical failure in an exception or nested group."""
    pending = [exc]
    while pending:
        current = pending.pop()
        if isinstance(current, ExecutionFailure):
            return current
        if isinstance(current, BaseExceptionGroup):
            pending.extend(reversed(current.exceptions))
    return None


def extract_all_failures(exc: BaseException) -> list[ExecutionFailure]:
    """Return all ExecutionFailure instances found in an exception or group."""
    found: list[ExecutionFailure] = []
    pending = [exc]
    while pending:
        current = pending.pop()
        if isinstance(current, ExecutionFailure):
            found.append(current)
        if isinstance(current, BaseExceptionGroup):
            pending.extend(reversed(current.exceptions))
    return found


# ---------------------------------------------------------------------------
# Normalization helpers (FCC-grade)
# ---------------------------------------------------------------------------

def _trace_failure(kind: FailureKind, status: int, message: str, **fields: Any) -> None:
    trace_event(
        "failure.normalized",
        kind=kind.value,
        status_code=status,
        message=message,
        **fields,
    )


def normalize_http_failure(
    *,
    status_code: int,
    message: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    request_id: Optional[str] = None,
    upstream: Optional[Mapping[str, Any]] = None,
) -> ExecutionFailure:
    """Normalize an HTTP-style error into an ExecutionFailure."""
    # Map HTTP status → canonical FailureKind
    if status_code == 400:
        kind = FailureKind.INVALID_REQUEST
    elif status_code == 401:
        kind = FailureKind.AUTHENTICATION
    elif status_code == 403:
        kind = FailureKind.PERMISSION
    elif status_code == 429:
        kind = FailureKind.RATE_LIMIT
    elif status_code == 408:
        kind = FailureKind.TIMEOUT
    elif status_code >= 500:
        kind = FailureKind.UPSTREAM
    else:
        kind = FailureKind.UNAVAILABLE

    retryable = kind in {
        FailureKind.RATE_LIMIT,
        FailureKind.TIMEOUT,
        FailureKind.OVERLOADED,
        FailureKind.UPSTREAM,
    }

    _trace_failure(kind, status_code, message, provider=provider, model=model)

    return ExecutionFailure(
        kind=kind,
        status_code=status_code,
        message=message,
        retryable=retryable,
        provider=provider,
        model=model,
        request_id=request_id,
        upstream=upstream,
    )


def normalize_provider_error(
    exc: BaseException,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    request_id: Optional[str] = None,
    upstream: Optional[Mapping[str, Any]] = None,
) -> ExecutionFailure:
    """Normalize arbitrary provider exceptions into an ExecutionFailure."""
    message = str(exc) or exc.__class__.__name__

    # Best-effort mapping based on common provider error patterns
    text = message.lower()

    if "context" in text and "token" in text:
        kind = FailureKind.CONTEXT_WINDOW_EXCEEDED
        status = 400
        retryable = False
    elif "rate" in text and "limit" in text:
        kind = FailureKind.RATE_LIMIT
        status = 429
        retryable = True
    elif "timeout" in text:
        kind = FailureKind.TIMEOUT
        status = 408
        retryable = True
    elif "auth" in text or "key" in text or "token" in text:
        kind = FailureKind.AUTHENTICATION
        status = 401
        retryable = False
    elif "permission" in text or "forbidden" in text:
        kind = FailureKind.PERMISSION
        status = 403
        retryable = False
    elif "overload" in text or "capacity" in text:
        kind = FailureKind.OVERLOADED
        status = 503
        retryable = True
    else:
        kind = FailureKind.UPSTREAM
        status = 500
        retryable = True

    _trace_failure(kind, status, message, provider=provider, model=model)

    return ExecutionFailure(
        kind=kind,
        status_code=status,
        message=message,
        retryable=retryable,
        provider=provider,
        model=model,
        request_id=request_id,
        upstream=upstream,
    )


# ---------------------------------------------------------------------------
# Convenience constructors
# ---------------------------------------------------------------------------

def failure_invalid_request(message: str, **fields: Any) -> ExecutionFailure:
    return ExecutionFailure(FailureKind.INVALID_REQUEST, 400, message, False, **fields)

def failure_timeout(message: str, **fields: Any) -> ExecutionFailure:
    return ExecutionFailure(FailureKind.TIMEOUT, 408, message, True, **fields)

def failure_rate_limit(message: str, **fields: Any) -> ExecutionFailure:
    return ExecutionFailure(FailureKind.RATE_LIMIT, 429, message, True, **fields)

def failure_auth(message: str, **fields: Any) -> ExecutionFailure:
    return ExecutionFailure(FailureKind.AUTHENTICATION, 401, message, False, **fields)

def failure_permission(message: str, **fields: Any) -> ExecutionFailure:
    return ExecutionFailure(FailureKind.PERMISSION, 403, message, False, **fields)

def failure_unavailable(message: str, **fields: Any) -> ExecutionFailure:
    return ExecutionFailure(FailureKind.UNAVAILABLE, 503, message, True, **fields)
