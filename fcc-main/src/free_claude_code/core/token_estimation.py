"""Process-wide best-effort plain-text token estimation for Free Claude Code.

This module provides:

- Backwards-compatible `estimate_text_tokens(text: str) -> int`.
- Provider-aware, model-sensitive token estimation helpers.
- Multi-encoder fallback chain with safe-to-fail behavior.
- Lightweight caching to avoid repeated expensive tokenization.
- Integration with core logging and tracing (when available).

It is designed to NEVER hard-fail FCC if tokenization is unavailable.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Protocol, Optional

try:
    import tiktoken
except Exception:  # noqa: BLE001
    tiktoken = None  # type: ignore[assignment]

try:
    from .logging_integration import log_with_context  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    def log_with_context(message: str, level: str = "info", **context: object) -> None:  # type: ignore[func-returns-value]
        # Best-effort fallback: no-op logging.
        return


try:
    from .trace import trace_event  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    def trace_event(event: str, **fields: object) -> None:  # type: ignore[func-returns-value]
        # Best-effort fallback: no-op tracing.
        return


_DISALLOWED_SPECIAL: tuple[str, ...] = ()


class _TokenEncoder(Protocol):
    """Protocol for token encoders used by FCC."""

    def encode(
        self,
        text: str,
        *,
        disallowed_special: tuple[str, ...],
    ) -> list[int]:
        ...


# ---------------------------------------------------------------------------
# Encoder loading and fallback chain
# ---------------------------------------------------------------------------


def _log_encoder_warning(encoding_name: str, exc: Exception) -> None:
    log_with_context(
        "Token encoder unavailable; falling back to approximate token estimates.",
        level="warning",
        encoding=encoding_name,
        error_type=type(exc).__name__,
        error=str(exc),
    )


def _try_get_encoding(name: str) -> Optional[_TokenEncoder]:
    """Best-effort wrapper around tiktoken.get_encoding."""
    if tiktoken is None:
        return None
    try:
        return tiktoken.get_encoding(name)  # type: ignore[no-any-return]
    except Exception as exc:  # noqa: BLE001
        _log_encoder_warning(name, exc)
        return None


@lru_cache(maxsize=8)
def _load_default_encoder() -> Optional[_TokenEncoder]:
    """Load the default encoder used by FCC for generic text."""
    # Primary: cl100k_base (OpenAI GPT-4/GPT-3.5 style)
    encoder = _try_get_encoding("cl100k_base")
    if encoder is not None:
        return encoder

    # Secondary: o200k_base (newer OpenAI models)
    encoder = _try_get_encoding("o200k_base")
    if encoder is not None:
        return encoder

    # Tertiary: p50k_base (older GPT-3 style)
    encoder = _try_get_encoding("p50k_base")
    if encoder is not None:
        return encoder

    # If all fail, return None and rely on approximate estimation.
    return None


@lru_cache(maxsize=32)
def _load_encoder_for_model(model_id: str) -> Optional[_TokenEncoder]:
    """Load an encoder tuned for a specific model ID, if possible.

    This is intentionally conservative and best-effort: if we cannot
    determine a better encoder, we fall back to the default encoder.
    """
    # Simple heuristics; can be expanded as FCC gains more providers.
    normalized = model_id.lower()

    # OpenAI-style models
    if normalized.startswith("gpt-") or "o3" in normalized or "o1" in normalized:
        encoder = _try_get_encoding("cl100k_base")
        if encoder is not None:
            return encoder

    # Anthropic-style models (Claude) – tiktoken does not have official encoders,
    # so we fall back to default.
    if "claude" in normalized:
        return _load_default_encoder()

    # DeepSeek / other BPE-based models – default encoder is usually fine.
    return _load_default_encoder()


# Process-wide default encoder (backwards-compatible global)
_ENCODER: Optional[_TokenEncoder] = _load_default_encoder()


# ---------------------------------------------------------------------------
# Core estimation helpers
# ---------------------------------------------------------------------------


def _approximate_token_count(text: str) -> int:
    """Approximate token count when no encoder is available.

    Uses a simple heuristic: ~4 characters per token, with a minimum of 1
    for non-empty strings.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def _encode_with_encoder(encoder: _TokenEncoder, text: str) -> int:
    """Safely encode text with a given encoder, with error handling."""
    try:
        tokens = encoder.encode(text, disallowed_special=_DISALLOWED_SPECIAL)
        return len(tokens)
    except Exception as exc:  # noqa: BLE001
        log_with_context(
            "Token encoder failed; falling back to approximate token estimates.",
            level="warning",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return _approximate_token_count(text)


@lru_cache(maxsize=1024)
def _estimate_text_tokens_cached(text: str) -> int:
    """Cached core implementation for plain-text token estimation."""
    if not text:
        return 0

    encoder = _ENCODER
    if encoder is None:
        return _approximate_token_count(text)

    return _encode_with_encoder(encoder, text)


# ---------------------------------------------------------------------------
# Public API (backwards-compatible)
# ---------------------------------------------------------------------------


def estimate_text_tokens(text: str) -> int:
    """Estimate tokens for plain text using the shared process-wide encoder.

    Backwards-compatible entrypoint used throughout FCC.

    - If a tiktoken encoder is available, uses it.
    - If not, falls back to a simple approximate heuristic.
    - Never raises on encoder failure; always returns an integer.
    """
    trace_event("token_estimation:start", mode="default", text_len=len(text))
    count = _estimate_text_tokens_cached(text)
    trace_event("token_estimation:complete", mode="default", tokens=count)
    return count


# ---------------------------------------------------------------------------
# Extended FCC helpers (new, but non-breaking)
# ---------------------------------------------------------------------------


def estimate_text_tokens_for_model(text: str, model_id: Optional[str]) -> int:
    """Estimate tokens for text given a specific model ID.

    This is an extended helper that does NOT change the original API.

    - If model_id is provided, attempts to load a model-specific encoder.
    - If that fails, falls back to the default encoder.
    - If no encoder is available, uses approximate estimation.
    """
    trace_event(
        "token_estimation:start",
        mode="model",
        text_len=len(text),
        model_id=model_id or "<none>",
    )

    if not text:
        trace_event("token_estimation:complete", mode="model", tokens=0, model_id=model_id or "<none>")
        return 0

    encoder: Optional[_TokenEncoder] = None
    if model_id:
        encoder = _load_encoder_for_model(model_id)

    if encoder is None:
        encoder = _ENCODER

    if encoder is None:
        count = _approximate_token_count(text)
        trace_event("token_estimation:complete", mode="model", tokens=count, model_id=model_id or "<none>")
        return count

    count = _encode_with_encoder(encoder, text)
    trace_event("token_estimation:complete", mode="model", tokens=count, model_id=model_id or "<none>")
    return count


def estimate_batch_tokens(texts: Iterable[str]) -> int:
    """Estimate total tokens for a batch of texts.

    This is useful for planning cost/length for multi-message prompts.
    """
    total = 0
    for text in texts:
        total += estimate_text_tokens(text)
    return total


def estimate_batch_tokens_for_model(texts: Iterable[str], model_id: Optional[str]) -> int:
    """Estimate total tokens for a batch of texts for a specific model."""
    total = 0
    for text in texts:
        total += estimate_text_tokens_for_model(text, model_id)
    return total


def estimate_stream_tokens(chunks: Iterable[str]) -> int:
    """Estimate tokens for a stream of text chunks.

    This is designed for incremental generation or logging scenarios.
    """
    total = 0
    for chunk in chunks:
        total += estimate_text_tokens(chunk)
    return total


def estimate_stream_tokens_for_model(chunks: Iterable[str], model_id: Optional[str]) -> int:
    """Estimate tokens for a stream of text chunks for a specific model."""
    total = 0
    for chunk in chunks:
        total += estimate_text_tokens_for_model(chunk, model_id)
    return total
