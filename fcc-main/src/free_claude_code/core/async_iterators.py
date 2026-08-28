"""Enhanced lifecycle helpers for composed asynchronous iterators.

Features added:
- AsyncCloseable protocol (original)
- try_close_async_iterator (original)
- MultiCloseable for grouped cleanup
- close_all_async for multi-resource closing
- safe_async_context for cleanup-on-exit
- iterator exhaustion detection
- cancellation-safe cleanup
- structured cleanup results
- optional logging integration hook
"""

from __future__ import annotations

import asyncio
from typing import Protocol, runtime_checkable, Iterable, Any, Optional


# ---------------------------------------------------------------------------
# Core protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class AsyncCloseable(Protocol):
    """An object whose asynchronous iteration resources can be released."""

    async def aclose(self) -> None:
        ...


# ---------------------------------------------------------------------------
# Basic close helper (original)
# ---------------------------------------------------------------------------

async def try_close_async_iterator(value: object) -> Exception | None:
    """Close ``value`` when supported, returning ordinary cleanup failures.

    Cancellation remains control flow and propagates to the caller. Returning
    ordinary exceptions lets an owner observe cleanup failure without replacing
    the stream outcome that was already established.
    """
    if not isinstance(value, AsyncCloseable):
        return None
    try:
        await value.aclose()
    except Exception as exc:
        return exc
    return None


# ---------------------------------------------------------------------------
# Multi-resource closing
# ---------------------------------------------------------------------------

class MultiCloseResult:
    """Structured result for multi-resource cleanup."""

    def __init__(self):
        self.successes: list[Any] = []
        self.failures: list[tuple[Any, Exception]] = []

    def add_success(self, item: Any) -> None:
        self.successes.append(item)

    def add_failure(self, item: Any, exc: Exception) -> None:
        self.failures.append((item, exc))

    def __bool__(self) -> bool:
        return not self.failures


async def close_all_async(items: Iterable[Any]) -> MultiCloseResult:
    """Close all AsyncCloseable items, collecting successes and failures."""
    result = MultiCloseResult()
    for item in items:
        if isinstance(item, AsyncCloseable):
            try:
                await item.aclose()
                result.add_success(item)
            except Exception as exc:
                result.add_failure(item, exc)
    return result


# ---------------------------------------------------------------------------
# Async context manager helper
# ---------------------------------------------------------------------------

class safe_async_context:
    """
    Wrap an async resource so that it is always closed on exit.

    Example:
        async with safe_async_context(stream) as s:
            async for chunk in s:
                ...
    """

    def __init__(self, resource: AsyncCloseable):
        self.resource = resource

    async def __aenter__(self):
        return self.resource

    async def __aexit__(self, exc_type, exc, tb):
        try:
            await self.resource.aclose()
        except Exception:
            # swallow cleanup errors; caller can inspect logs if needed
            return False
        return False


# ---------------------------------------------------------------------------
# Iterator exhaustion detection
# ---------------------------------------------------------------------------

async def exhaust_async_iterator(aiter) -> None:
    """Consume an async iterator fully, ignoring yielded values."""
    async for _ in aiter:
        pass


async def exhaust_and_close(aiter: Any) -> Optional[Exception]:
    """Consume an async iterator fully, then close it if closeable."""
    try:
        await exhaust_async_iterator(aiter)
    except Exception as exc:
        # iterator failure; still attempt close
        close_exc = await try_close_async_iterator(aiter)
        return exc or close_exc

    return await try_close_async_iterator(aiter)


# ---------------------------------------------------------------------------
# Cancellation-safe cleanup
# ---------------------------------------------------------------------------

async def cancel_and_close(task: asyncio.Task, resource: Any) -> Optional[Exception]:
    """
    Cancel a task and close a resource safely.

    Returns:
        Exception if cleanup fails, otherwise None.
    """
    try:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    except Exception:
        # task cancellation failed; still attempt close
        return await try_close_async_iterator(resource)

    return await try_close_async_iterator(resource)


# ---------------------------------------------------------------------------
# Optional logging hook (non-required, safe-to-fail)
# ---------------------------------------------------------------------------

def log_cleanup_failure(item: Any, exc: Exception) -> None:
    """Optional logging hook for cleanup failures."""
    try:
        from .logging_integration import log_with_context
        log_with_context(
            f"Async cleanup failure: {exc}",
            level="error",
            item=str(item),
        )
    except Exception:
        # logging is optional; swallow errors
        pass
