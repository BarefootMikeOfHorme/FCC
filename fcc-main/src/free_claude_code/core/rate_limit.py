"""
FCC Strict Sliding‑Window Rate Limiter
--------------------------------------

Enhancements:
- Structured trace events
- Logging integration with safe‑to‑fail guards
- Provider/model/session metadata fields
- Deterministic sliding‑window semantics
- Backwards compatible API
"""

import asyncio
import time
from collections import deque
from collections.abc import Callable
from typing import Optional

# FCC integrations
try:
    from .trace import trace_event
except Exception:
    def trace_event(event: str, **fields): pass

try:
    from .logging_integration import log_with_context
except Exception:
    def log_with_context(msg: str, level: str = "info", **ctx): pass


class StrictSlidingWindowLimiter:
    """
    Strict sliding window limiter.

    Guarantees: at most `rate_limit` acquisitions in any interval of length
    `rate_window` seconds.

    FCC Enhancements:
    - provider/model/session metadata
    - structured trace events
    - safe‑to‑fail logging
    - deterministic monotonic timestamps
    """

    def __init__(
        self,
        rate_limit: int,
        rate_window: float,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:

        if rate_limit <= 0:
            raise ValueError("rate_limit must be > 0")
        if rate_window <= 0:
            raise ValueError("rate_window must be > 0")

        self._rate_limit = int(rate_limit)
        self._rate_window = float(rate_window)
        self._times: deque[float] = deque()
        self._lock = asyncio.Lock()

        self.provider = provider
        self.model = model
        self.session_id = session_id

        trace_event(
            "rate_limit.init",
            rate_limit=self._rate_limit,
            rate_window=self._rate_window,
            provider=self.provider,
            model=self.model,
            session_id=self.session_id,
        )

    async def acquire(self) -> None:
        await self._acquire(None)

    async def acquire_if(self, allowed: Callable[[], bool]) -> bool:
        """
        Record an acquisition only if `allowed()` still holds at admission.

        Capacity is awaited first. The synchronous condition and timestamp write
        then run without yielding, so a rejected admission consumes no quota.
        """
        return await self._acquire(allowed)

    async def _acquire(self, allowed: Callable[[], bool] | None) -> bool:
        while True:
            wait_time = 0.0

            async with self._lock:
                now = time.monotonic()
                cutoff = now - self._rate_window

                # Remove expired timestamps
                while self._times and self._times[0] <= cutoff:
                    self._times.popleft()

                # Capacity available
                if len(self._times) < self._rate_limit:
                    if allowed is not None and not allowed():
                        trace_event(
                            "rate_limit.reject",
                            provider=self.provider,
                            model=self.model,
                            session_id=self.session_id,
                        )
                        return False

                    ts = time.monotonic()
                    self._times.append(ts)

                    trace_event(
                        "rate_limit.acquire",
                        timestamp=ts,
                        provider=self.provider,
                        model=self.model,
                        session_id=self.session_id,
                        used=len(self._times),
                        limit=self._rate_limit,
                    )

                    return True

                # No capacity — compute wait time
                oldest = self._times[0]
                wait_time = max(0.0, (oldest + self._rate_window) - now)

                trace_event(
                    "rate_limit.wait",
                    wait_time=wait_time,
                    provider=self.provider,
                    model=self.model,
                    session_id=self.session_id,
                    used=len(self._times),
                    limit=self._rate_limit,
                )

            # Sleep outside the lock
            try:
                await asyncio.sleep(wait_time if wait_time > 0 else 0)
            except Exception as e:
                log_with_context(
                    "Rate limiter sleep failed.",
                    level="warning",
                    error=str(e),
                    provider=self.provider,
                    model=self.model,
                    session_id=self.session_id,
                )
                await asyncio.sleep(0)

    async def __aenter__(self) -> "StrictSlidingWindowLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False
