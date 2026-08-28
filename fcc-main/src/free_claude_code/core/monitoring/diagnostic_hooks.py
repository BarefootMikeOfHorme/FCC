"""
diagnostic_hooks.py

L1 protocol debugging hooks.

Non-intrusive: they only observe, never modify behavior.
"""

from typing import Dict, Any, Callable, List


class DiagnosticHooks:
    def __init__(self) -> None:
        self._hooks: List[Callable[[Dict[str, Any]], None]] = []

    def register(self, hook: Callable[[Dict[str, Any]], None]) -> None:
        if hook not in self._hooks:
            self._hooks.append(hook)

    def unregister(self, hook: Callable[[Dict[str, Any]], None]) -> None:
        if hook in self._hooks:
            self._hooks.remove(hook)

    def on_event(self, event: Dict[str, Any]) -> None:
        for hook in list(self._hooks):
            try:
                hook(event)
            except Exception:
                # Diagnostics must never affect core/L1
                continue
