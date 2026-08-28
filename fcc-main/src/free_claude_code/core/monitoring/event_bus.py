"""
event_bus.py

Dedicated event dispatcher for monitoring.

You can use this instead of or alongside orchestrator.emit().
"""

from typing import Callable, Dict, Any, List


class EventBus:
    def __init__(self) -> None:
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        if listener not in self._subscribers:
            self._subscribers.append(listener)

    def unsubscribe(self, listener: Callable[[Dict[str, Any]], None]) -> None:
        if listener in self._subscribers:
            self._subscribers.remove(listener)

    def emit(self, event: Dict[str, Any]) -> None:
        for listener in list(self._subscribers):
            try:
                listener(event)
            except Exception:
                # Never let monitoring events break core/L1
                continue
