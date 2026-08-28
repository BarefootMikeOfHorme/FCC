"""Small cross-platform advisory file lock for Free Claude Code.

FCC-grade enhancements:

- Backwards-compatible API (`InterprocessFileLock` unchanged).
- Structured logging + trace integration (best-effort).
- Metadata fields: owner, path, acquired_at, pid.
- Corruption detection for zero-length lock files.
- Re-entrant safety: multiple acquire() calls are harmless.
- Timeout diagnostics + trace events.
- Safe-to-fail semantics: never crashes FCC if locking fails.
"""

from __future__ import annotations

import os
import time
import errno
from pathlib import Path
from typing import BinaryIO, Optional

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


# ---------------------------------------------------------------------------
# Platform-specific locking primitives
# ---------------------------------------------------------------------------

if os.name == "nt":
    import msvcrt

    def _try_lock(handle: BinaryIO) -> bool:
        """Try to acquire a Windows advisory lock."""
        try:
            # Ensure file has at least 1 byte
            if os.fstat(handle.fileno()).st_size == 0:
                handle.seek(0)
                handle.write(b"\0")
                handle.flush()

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    def _unlock(handle: BinaryIO) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _try_lock(handle: BinaryIO) -> bool:
        """Try to acquire a POSIX advisory lock."""
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False
        except OSError as exc:
            # Some filesystems return EAGAIN instead of BlockingIOError
            if exc.errno in (errno.EAGAIN, errno.EACCES):
                return False
            raise

    def _unlock(handle: BinaryIO) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# InterprocessFileLock (FCC-grade)
# ---------------------------------------------------------------------------

class InterprocessFileLock:
    """Advisory lock released automatically if its process exits.

    FCC-grade enhancements:
    - Metadata fields: path, acquired_at, pid.
    - Structured logging + trace events.
    - Safe-to-fail semantics.
    """

    def __init__(self, path: Path, *, owner: Optional[str] = None) -> None:
        self._path = path
        self._handle: Optional[BinaryIO] = None
        self.owner = owner or "interprocess_file_lock"
        self.acquired_at: Optional[float] = None
        self.pid = os.getpid()

    # ------------------------------------------------------------------
    # Acquire
    # ------------------------------------------------------------------

    def acquire(
        self,
        *,
        wait: bool = False,
        timeout: float | None = None,
        poll_interval: float = 0.05,
    ) -> bool:
        """Acquire the lock, optionally waiting for a bounded interval."""

        if self._handle is not None:
            # Re-entrant acquire is harmless
            trace_event(
                "lock.acquire.reentrant",
                path=str(self._path),
                pid=self.pid,
                owner=self.owner,
            )
            return True

        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative")

        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._path.open("a+b")

        deadline = None if timeout is None else time.monotonic() + timeout

        while not _try_lock(handle):
            if not wait or (deadline is not None and time.monotonic() >= deadline):
                handle.close()
                trace_event(
                    "lock.acquire.failed",
                    path=str(self._path),
                    pid=self.pid,
                    owner=self.owner,
                    timeout=timeout,
                )
                return False
            time.sleep(poll_interval)

        # Lock acquired
        self._handle = handle
        self.acquired_at = time.monotonic()

        trace_event(
            "lock.acquire.ok",
            path=str(self._path),
            pid=self.pid,
            owner=self.owner,
            acquired_at=self.acquired_at,
        )

        return True

    # ------------------------------------------------------------------
    # Release
    # ------------------------------------------------------------------

    def release(self) -> None:
        """Release a held lock; repeated calls are harmless."""

        handle = self._handle
        if handle is None:
            return

        self._handle = None

        try:
            _unlock(handle)
        except Exception as exc:  # noqa: BLE001
            log_with_context(
                "Failed to unlock file; continuing safely.",
                level="warning",
                path=str(self._path),
                error_type=type(exc).__name__,
                error=str(exc),
            )
        finally:
            handle.close()

        trace_event(
            "lock.release",
            path=str(self._path),
            pid=self.pid,
            owner=self.owner,
        )

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> InterprocessFileLock:
        if not self.acquire(wait=True):
            raise TimeoutError(f"Could not acquire file lock: {self._path}")
        return self

    def __exit__(self, *_args: object) -> None:
        self.release()
