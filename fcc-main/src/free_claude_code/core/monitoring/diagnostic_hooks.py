"""
L1 protocol diagnostic hooks.

Non-intrusive: they only observe events and never modify behavior.
Useful for debugging, tracing, and lightweight instrumentation.
"""

from typing import Any, Dict, List
from collections.abc import Callable


class DiagnosticHooks:
    """
    A minimal observer-style hook registry for protocol diagnostics.

    Hooks are simple callables that receive an event dictionary.
    They must never raise exceptions that affect core behavior.
    """

    def __init__(self) -> None:
        # Each hook: Callable[[Dict[str, Any]], None]
        self._hooks: List[Callable[[Dict[str, Any]], None]] = []

    def register(self, hook: Callable[[Dict[str, Any]], None]) -> None:
        """Register a diagnostic hook if not already present."""
        if hook not in self._hooks:
            self._hooks.append(hook)

    def unregister(self, hook: Callable[[Dict[str, Any]], None]) -> None:
        """Remove a previously registered diagnostic hook."""
        if hook in self._hooks:
            self._hooks.remove(hook)

    def on_event(self, event: Dict[str, Any]) -> None:
        """
        Dispatch an event to all registered hooks.

        Hooks are isolated: exceptions are swallowed to ensure
        diagnostics never interfere with protocol execution.
        """
        for hook in list(self._hooks):
            try:
                hook(event)
            except Exception:
                # Diagnostics must never affect core/L1 behavior.
                continue
