"""Gateway-safe model ID encoding shared by API and CLI adapters.

This FCC-grade enhanced module provides:

- Backwards-compatible gateway model ID encoding/decoding.
- Provider-aware normalization helpers.
- Structured logging + trace integration (best-effort).
- Validation helpers for gateway-safe model IDs.
- Convenience utilities for reversible routing.
- Rich metadata fields for decoded model IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

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
# Constants
# ---------------------------------------------------------------------------

GATEWAY_MODEL_ID_PREFIX = "anthropic"
NO_THINKING_GATEWAY_MODEL_ID_PREFIX = "claude-3-freecc-no-thinking"

# Provider prefixes FCC recognizes for routing
KNOWN_PROVIDER_PREFIXES = frozenset(
    [
        "anthropic",
        "openai",
        "deepseek",
        "nvidia",
        "google",
        "mistral",
        "meta",
    ]
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DecodedGatewayModelId:
    """Decoded gateway model ID with routing metadata."""

    provider_id: str
    provider_model: str
    force_reasoning_off: bool = False
    raw: Optional[str] = None

    def __post_init__(self) -> None:
        # Ensure immutability and safe defaults
        if self.raw is None:
            object.__setattr__(self, "raw", f"{self.provider_id}/{self.provider_model}")


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

def gateway_model_id(provider_model_ref: str) -> str:
    """Return the normal Claude Code-discoverable id for a provider/model ref."""
    encoded = f"{GATEWAY_MODEL_ID_PREFIX}/{provider_model_ref}"
    trace_event("gateway.encode", encoded=encoded, provider_model_ref=provider_model_ref)
    return encoded


def no_thinking_gateway_model_id(provider_model_ref: str) -> str:
    """Return a Claude Code-discoverable id that disables client thinking."""
    encoded = f"{NO_THINKING_GATEWAY_MODEL_ID_PREFIX}/{provider_model_ref}"
    trace_event(
        "gateway.encode.no_thinking",
        encoded=encoded,
        provider_model_ref=provider_model_ref,
    )
    return encoded


# ---------------------------------------------------------------------------
# Decoding helpers
# ---------------------------------------------------------------------------

def decode_gateway_model_id(model_name: str) -> Optional[DecodedGatewayModelId]:
    """Decode a model id advertised by this gateway, if it is one."""
    prefix, separator, remainder = model_name.partition("/")
    if not separator:
        return None

    if prefix == GATEWAY_MODEL_ID_PREFIX:
        force_reasoning_off = False
    elif prefix == NO_THINKING_GATEWAY_MODEL_ID_PREFIX:
        force_reasoning_off = True
    else:
        return None

    provider_id, provider_separator, provider_model = remainder.partition("/")
    if not provider_separator or not provider_model:
        return None

    decoded = DecodedGatewayModelId(
        provider_id=provider_id,
        provider_model=provider_model,
        force_reasoning_off=force_reasoning_off,
        raw=model_name,
    )

    trace_event(
        "gateway.decode",
        model_name=model_name,
        provider_id=provider_id,
        provider_model=provider_model,
        force_reasoning_off=force_reasoning_off,
    )

    return decoded


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def is_gateway_model_id(model_name: str) -> bool:
    """Return True if the model name is a gateway-safe encoded ID."""
    prefix, sep, _ = model_name.partition("/")
    return sep and prefix in (
        GATEWAY_MODEL_ID_PREFIX,
        NO_THINKING_GATEWAY_MODEL_ID_PREFIX,
    )


def is_known_provider(provider_id: str) -> bool:
    """Return True if provider_id is recognized by FCC routing."""
    return provider_id.lower() in KNOWN_PROVIDER_PREFIXES


def validate_gateway_model_id(model_name: str) -> bool:
    """Return True if the model name is valid and decodable."""
    decoded = decode_gateway_model_id(model_name)
    if decoded is None:
        return False
    return bool(decoded.provider_id and decoded.provider_model)


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------

def provider_and_model(model_name: str) -> tuple[Optional[str], Optional[str]]:
    """Return (provider_id, provider_model) for any gateway-safe model ID."""
    decoded = decode_gateway_model_id(model_name)
    if decoded is None:
        return None, None
    return decoded.provider_id, decoded.provider_model


def force_reasoning_off(model_name: str) -> bool:
    """Return True if the gateway model ID disables client-side reasoning."""
    decoded = decode_gateway_model_id(model_name)
    return bool(decoded and decoded.force_reasoning_off)
