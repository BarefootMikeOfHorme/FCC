"""Unified JSON / JSONC / YAML / MD / CBOR value vocabulary for FCC.

This module provides:
- JSON type aliases (scalar, value, object, array, dict)
- JSONC parsing (strip comments)
- YAML parsing (safe loader)
- Markdown extraction helpers
- CBOR encoding/decoding
- Unified load_any() / dump_any() helpers
- JSON-safe sanitization
- JsonSerializable protocol
- JsonError exception

Fully backwards compatible with the original FCC json_types.py.
"""

from __future__ import annotations

import json
import re
from typing import Any, Protocol
from collections.abc import Mapping, Sequence

# Optional imports
try:
    import yaml
except Exception:
    yaml = None

try:
    import cbor2
except Exception:
    cbor2 = None


# ---------------------------------------------------------------------------
# Core JSON type vocabulary
# ---------------------------------------------------------------------------

type JsonScalar = bool | int | float | str | None
type JsonPrimitive = JsonScalar

type JsonValue = JsonScalar | Sequence["JsonValue"] | Mapping[str, "JsonValue"]
type JsonArray = list[JsonValue]
type JsonDict = dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]  # Backwards-compatible alias


# ---------------------------------------------------------------------------
# JsonSerializable protocol
# ---------------------------------------------------------------------------

class JsonSerializable(Protocol):
    """Objects implementing this protocol can be serialized into JSONValue."""

    def to_json(self) -> JsonValue:
        ...


# ---------------------------------------------------------------------------
# JSON error class
# ---------------------------------------------------------------------------

class JsonError(Exception):
    """Raised when JSON validation or conversion fails."""
    pass


# ---------------------------------------------------------------------------
# JSON validation helpers
# ---------------------------------------------------------------------------

def is_json_scalar(value: Any) -> bool:
    return (
        value is None
        or isinstance(value, (bool, int, float, str))
    )


def is_json_value(value: Any) -> bool:
    if is_json_scalar(value):
        return True

    if isinstance(value, Mapping):
        return all(
            isinstance(k, str) and is_json_value(v)
            for k, v in value.items()
        )

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return all(is_json_value(v) for v in value)

    return False


# ---------------------------------------------------------------------------
# JSON-safe sanitization
# ---------------------------------------------------------------------------

def ensure_json_safe(value: Any) -> JsonValue:
    """Convert arbitrary Python values into JSON-safe equivalents."""
    if is_json_scalar(value):
        return value

    if isinstance(value, JsonSerializable):
        try:
            return ensure_json_safe(value.to_json())
        except Exception as exc:
            raise JsonError(f"JsonSerializable.to_json() failed: {exc}") from exc

    if isinstance(value, Mapping):
        safe_dict: JsonDict = {}
        for k, v in value.items():
            key = str(k) if not isinstance(k, str) else k
            safe_dict[key] = ensure_json_safe(v)
        return safe_dict

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [ensure_json_safe(v) for v in value]

    return str(value)


# ---------------------------------------------------------------------------
# JSONC support (strip comments)
# ---------------------------------------------------------------------------

_JSONC_COMMENT_RE = re.compile(
    r"""
    (//[^\n]*$)     |   # line comments
    (/\*.*?\*/)         # block comments
    """,
    re.MULTILINE | re.DOTALL | re.VERBOSE,
)

def strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments from JSONC."""
    return _JSONC_COMMENT_RE.sub("", text)


# ---------------------------------------------------------------------------
# YAML support
# ---------------------------------------------------------------------------

def load_yaml(text: str) -> JsonValue:
    if yaml is None:
        raise JsonError("YAML support not available (PyYAML not installed)")
    try:
        data = yaml.safe_load(text)
    except Exception as exc:
        raise JsonError(f"YAML parse failed: {exc}") from exc
    return ensure_json_safe(data)


# ---------------------------------------------------------------------------
# Markdown support
# ---------------------------------------------------------------------------

def extract_markdown_json(text: str) -> JsonValue:
    """
    Extract JSON from Markdown code blocks.

    Example:
    ```json
    { "a": 1 }
    ```
    """
    code_block_re = re.compile(
        r"```(?:json)?\s*(.*?)```",
        re.DOTALL | re.IGNORECASE,
    )
    match = code_block_re.search(text)
    if not match:
        raise JsonError("No JSON code block found in Markdown")
    return json_load(match.group(1))


# ---------------------------------------------------------------------------
# CBOR support
# ---------------------------------------------------------------------------

def load_cbor(data: bytes) -> JsonValue:
    if cbor2 is None:
        raise JsonError("CBOR support not available (cbor2 not installed)")
    try:
        value = cbor2.loads(data)
    except Exception as exc:
        raise JsonError(f"CBOR decode failed: {exc}") from exc
    return ensure_json_safe(value)


def dump_cbor(value: JsonValue) -> bytes:
    if cbor2 is None:
        raise JsonError("CBOR support not available (cbor2 not installed)")
    try:
        return cbor2.dumps(ensure_json_safe(value))
    except Exception as exc:
        raise JsonError(f"CBOR encode failed: {exc}") from exc


# ---------------------------------------------------------------------------
# JSON load/dump wrappers
# ---------------------------------------------------------------------------

def json_dump(obj: JsonValue, *, indent: int | None = None) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=indent)
    except Exception as exc:
        raise JsonError(f"json_dump failed: {exc}") from exc


def json_load(text: str) -> JsonValue:
    try:
        value = json.loads(text)
    except Exception as exc:
        raise JsonError(f"json_load failed: {exc}") from exc

    if not is_json_value(value):
        raise JsonError("Loaded value is not valid JsonValue")

    return value


# ---------------------------------------------------------------------------
# Unified multi-format loader
# ---------------------------------------------------------------------------

def load_any(data: Any, *, format: str | None = None) -> JsonValue:
    """
    Load JSON/YAML/JSONC/MD/CBOR depending on format or auto-detection.

    format options:
    - "json"
    - "jsonc"
    - "yaml"
    - "md"
    - "cbor"
    - None (auto-detect)
    """
    if format == "json":
        return json_load(data)

    if format == "jsonc":
        return json_load(strip_jsonc(data))

    if format == "yaml":
        return load_yaml(data)

    if format == "md":
        return extract_markdown_json(data)

    if format == "cbor":
        return load_cbor(data)

    # Auto-detect
    if isinstance(data, bytes):
        return load_cbor(data)

    text = str(data).strip()

    if text.startswith("{") or text.startswith("["):
        try:
            return json_load(text)
        except Exception:
            return json_load(strip_jsonc(text))

    if yaml is not None:
        try:
            return load_yaml(text)
        except Exception:
            pass

    try:
        return extract_markdown_json(text)
    except Exception:
        pass

    raise JsonError("Unable to auto-detect format for load_any")


# ---------------------------------------------------------------------------
# Unified multi-format dumper
# ---------------------------------------------------------------------------

def dump_any(value: JsonValue, *, format: str = "json") -> Any:
    """
    Dump JSON/YAML/CBOR depending on format.

    format options:
    - "json"
    - "yaml"
    - "cbor"
    """
    if format == "json":
        return json_dump(value, indent=2)

    if format == "yaml":
        if yaml is None:
            raise JsonError("YAML support not available")
        return yaml.safe_dump(ensure_json_safe(value), sort_keys=False)

    if format == "cbor":
        return dump_cbor(value)

    raise JsonError(f"Unknown dump format: {format}")


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def as_json_dict(obj: Any) -> JsonDict:
    safe = ensure_json_safe(obj)
    if isinstance(safe, Mapping):
        return dict(safe)
    raise JsonError("Object cannot be converted to JsonDict")


def as_json_array(obj: Any) -> JsonArray:
    safe = ensure_json_safe(obj)
    if isinstance(safe, Sequence) and not isinstance(safe, (str, bytes, bytearray)):
        return list(safe)
    raise JsonError("Object cannot be converted to JsonArray")
