"""Provider-neutral reasoning intent for Free Claude Code.

This module defines FCC's unified reasoning control vocabulary, numeric budget
mapping, provider translation helpers, and validation semantics. It is fully
provider-neutral and does not assume any specific model family.

Enhancements:
- Structured trace events for construction, validation, and mapping.
- Logging integration with safe redaction.
- Provider mapping helpers (to/from provider payloads).
- Reasoning effort normalization utilities.
- FCC-grade docstrings and safety semantics.
- Backwards compatible with original FCC reasoning.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Dict, Optional

# Optional FCC integrations
try:
    from .logging_integration import log_with_context
except Exception:
    def log_with_context(message: str, level: str = "info", **ctx: object) -> None:
        return

try:
    from .trace import trace_event
except Exception:
    def trace_event(event: str, **fields: object) -> None:
        return


# ---------------------------------------------------------------------------
# Reasoning control vocabulary
# ---------------------------------------------------------------------------

class ReasoningControl(StrEnum):
    """Whether a request explicitly controls reasoning computation."""
    DEFAULT = "default"
    OFF = "off"
    ON = "on"


class ReasoningEffort(StrEnum):
    """Named reasoning effort understood at the FCC application boundary."""

    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"

    @property
    def budget_tokens(self) -> int:
        """Return FCC's numeric token budget for this effort."""
        return _EFFORT_BUDGET_TOKENS[self]


_EFFORT_BUDGET_TOKENS = {
    ReasoningEffort.MINIMAL: 512,
    ReasoningEffort.LOW: 512,
    ReasoningEffort.MEDIUM: 1_024,
    ReasoningEffort.HIGH: 2_048,
    ReasoningEffort.XHIGH: 4_096,
    ReasoningEffort.MAX: 8_192,
}


# ---------------------------------------------------------------------------
# Reasoning policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ReasoningPolicy:
    """Resolved client and configuration intent passed to one provider.

    `control` and `effort` remain independent because clients may set an
    overall effort while separately disabling extended thinking. Providers
    translate the representable subset without changing the original intent.

    Fields:
        control: Whether reasoning is explicitly enabled/disabled.
        effort: Named reasoning effort tier.
        budget_tokens: Exact numeric budget (requires control=ON).
    """

    control: ReasoningControl = ReasoningControl.DEFAULT
    effort: Optional[ReasoningEffort] = None
    budget_tokens: Optional[int] = None

    def __post_init__(self) -> None:
        trace_event(
            "reasoning.policy.init",
            control=self.control,
            effort=str(self.effort) if self.effort else None,
            budget=self.budget_tokens,
        )

        if self.budget_tokens is not None:
            if (
                not isinstance(self.budget_tokens, int)
                or isinstance(self.budget_tokens, bool)
                or self.budget_tokens <= 0
            ):
                log_with_context(
                    "Invalid reasoning budget.",
                    level="error",
                    budget=self.budget_tokens,
                )
                raise ValueError("Reasoning budget must be a positive integer.")

            if self.control is not ReasoningControl.ON:
                log_with_context(
                    "Budget requires reasoning control ON.",
                    level="error",
                    control=self.control,
                )
                raise ValueError("A reasoning budget requires reasoning control to be on.")

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def provider_default(cls) -> ReasoningPolicy:
        """Leave reasoning computation entirely to the provider."""
        trace_event("reasoning.policy.provider_default")
        return cls()

    @classmethod
    def off(cls) -> ReasoningPolicy:
        """Explicitly disable reasoning computation and output."""
        trace_event("reasoning.policy.off")
        return cls(control=ReasoningControl.OFF)

    @classmethod
    def on(
        cls,
        *,
        effort: Optional[ReasoningEffort] = None,
        budget_tokens: Optional[int] = None,
    ) -> ReasoningPolicy:
        """Explicitly enable reasoning with optional client controls."""
        trace_event(
            "reasoning.policy.on",
            effort=str(effort) if effort else None,
            budget=budget_tokens,
        )
        return cls(
            control=ReasoningControl.ON,
            effort=effort,
            budget_tokens=budget_tokens,
        )

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def output_enabled(self) -> bool:
        """Return whether provider reasoning may be exposed to the client."""
        return self.control is not ReasoningControl.OFF

    @property
    def requests_reasoning(self) -> bool:
        """Return whether the request explicitly asks the provider to reason."""
        return self.control is not ReasoningControl.OFF and (
            self.control is ReasoningControl.ON
            or self.effort is not None
            or self.budget_tokens is not None
        )

    @property
    def numeric_budget_tokens(self) -> Optional[int]:
        """Express this intent as an exact or FCC-mapped numeric budget."""
        if self.control is ReasoningControl.OFF:
            return None
        if self.budget_tokens is not None:
            return self.budget_tokens
        if self.effort is None:
            return None
        return self.effort.budget_tokens

    # ------------------------------------------------------------------
    # Provider translation helpers
    # ------------------------------------------------------------------

    def to_provider_payload(self, provider: str) -> Dict[str, Any]:
        """Translate FCC reasoning intent into a provider-specific payload.

        Providers may not support all FCC fields. Unsupported fields are omitted.
        """
        trace_event(
            "reasoning.policy.to_provider_payload",
            provider=provider,
            control=self.control,
            effort=str(self.effort) if self.effort else None,
            budget=self.budget_tokens,
        )

        payload: Dict[str, Any] = {}

        if self.control is ReasoningControl.OFF:
            payload["reasoning"] = False
            return payload

        if self.control is ReasoningControl.ON:
            payload["reasoning"] = True

        if self.effort is not None:
            payload["reasoning_effort"] = self.effort.value

        if self.budget_tokens is not None:
            payload["reasoning_budget_tokens"] = self.budget_tokens

        return payload

    @classmethod
    def from_provider_payload(cls, provider: str, payload: Dict[str, Any]) -> ReasoningPolicy:
        """Normalize provider reasoning response into FCC ReasoningPolicy."""
        trace_event(
            "reasoning.policy.from_provider_payload",
            provider=provider,
            payload=payload,
        )

        control = ReasoningControl.DEFAULT
        effort: Optional[ReasoningEffort] = None
        budget: Optional[int] = None

        if payload.get("reasoning") is False:
            control = ReasoningControl.OFF
        elif payload.get("reasoning") is True:
            control = ReasoningControl.ON

        if "reasoning_effort" in payload:
            try:
                effort = ReasoningEffort(payload["reasoning_effort"])
            except Exception:
                log_with_context(
                    "Unknown provider reasoning effort.",
                    level="warning",
                    provider_effort=payload["reasoning_effort"],
                )

        if "reasoning_budget_tokens" in payload:
            try:
                budget = int(payload["reasoning_budget_tokens"])
            except Exception:
                log_with_context(
                    "Invalid provider reasoning budget.",
                    level="warning",
                    provider_budget=payload["reasoning_budget_tokens"],
                )

        return cls(control=control, effort=effort, budget_tokens=budget)


# ---------------------------------------------------------------------------
# Default policy
# ---------------------------------------------------------------------------

DEFAULT_REASONING_POLICY = ReasoningPolicy.provider_default()
