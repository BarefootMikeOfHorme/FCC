"""
Dedicated event dispatcher for monitoring.

This EventBus is intentionally lightweight and non-intrusive:
- Subscribers receive events but cannot block or modify dispatch.
- Errors in listeners are swallowed to ensure monitoring never affects core/L1.
"""

from __future__ import annotations

from typing import Callable, Dict, Any, List


class EventBus:
    def __init__(self) -> None:
        # Each subscriber is a callable:  listener(event_dict) -> None
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Register a listener if not already subscribed."""
        if listener not in self._subscribers:
            self._subscribers.append(listener)

    def unsubscribe(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        """Remove a previously registered listener."""
        if listener in self._subscribers:
            self._subscribers.remove(listener)

    def emit(self, event: Dict[str, Any]) -> None:
        """
        Dispatch an event to all subscribers.

        Monitoring must NEVER interfere with core/L1 behavior,
        so all listener exceptions are swallowed.
        """
        for listener in list(self._subscribers):
            try:
                listener(event)
            except Exception:
                # Never let monitoring events break core/L1
                continue
