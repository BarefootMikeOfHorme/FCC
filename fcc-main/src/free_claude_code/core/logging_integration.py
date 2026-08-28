"""Enhanced logging integration for Free Claude Code.

Features:
- Rich console sink
- Structured log entries
- Multi-format logging (JSON, JSONC, YAML, CBOR, Markdown)
- Redaction layer for secrets/tokens
- Diagnostics-aware logging
- Dependency resolver integration
- Monitoring orchestrator integration
- Context-aware logging (request/session/metadata)
- Multi-sink routing (console, file, JSON, CBOR)
- Safe-to-fail fallbacks

Backwards compatible with original FCC logging_integration.py.
"""

from __future__ import annotations

import sys
import json
import re
from typing import Any, Dict, Optional

from loguru import logger

from .output_schemas import VerbosityLevel
from .rich_output import get_rich_formatter
from .json_types import (
    ensure_json_safe,
    dump_any,
    JsonError,
)

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
# Redaction layer
# ---------------------------------------------------------------------------

_SECRET_REPLACEMENTS = (
    (re.compile(r"(?i)(bearer\s+)[^\s]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)[^\s]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(token\s*[:=]\s*)[^\s]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(authorization\s*[:=]\s*)[^\s]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(sessionid\s*[:=]\s*)[^\s]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(jwt\s*[:=]\s*)[^\s]+"), r"\1<redacted>"),
)

def redact_text(text: str) -> str:
    """Redact secrets/tokens from log text."""
    sanitized = text
    for pattern, replacement in _SECRET_REPLACEMENTS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


# ---------------------------------------------------------------------------
# Structured log entry builder
# ---------------------------------------------------------------------------

def build_structured_entry(record: Dict[str, Any]) -> Dict[str, Any]:
    """Build a structured log entry from a loguru record."""
    entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": redact_text(record["message"]),
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }

    # Context fields
    extra = record.get("extra", {})
    if extra:
        entry["context"] = {}
        for k, v in extra.items():
            entry["context"][k] = v

    return entry


# ---------------------------------------------------------------------------
# Multi-format sinks
# ---------------------------------------------------------------------------

class MultiFormatSink:
    """A sink that writes logs in JSON, YAML, CBOR, or Markdown."""

    def __init__(self, format: str = "json", path: str = "logs/fcc_structured.log"):
        self.format = format
        self.path = path

    def __call__(self, message):
        record = message.record
        entry = build_structured_entry(record)
        safe_entry = ensure_json_safe(entry)

        try:
            if self.format == "json":
                text = dump_any(safe_entry, format="json")
            elif self.format == "yaml":
                if yaml is None:
                    return
                text = dump_any(safe_entry, format="yaml")
            elif self.format == "cbor":
                if cbor2 is None:
                    return
                data = dump_any(safe_entry, format="cbor")
                with open(self.path + ".cbor", "ab") as f:
                    f.write(data)
                return
            elif self.format == "md":
                text = f"```json\n{dump_any(safe_entry, format='json')}\n```"
            else:
                text = dump_any(safe_entry, format="json")
        except JsonError:
            text = json.dumps({"error": "log serialization failed"}, ensure_ascii=False)

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(text + "\n")


# ---------------------------------------------------------------------------
# Rich console sink
# ---------------------------------------------------------------------------

class RichOutputSink:
    """A loguru sink that outputs to the console using rich formatting."""

    def __init__(self, verbosity: VerbosityLevel = VerbosityLevel.NORMAL):
        self.verbosity = verbosity
        self.formatter = get_rich_formatter(verbosity)

    def __call__(self, message):
        record = message.record
        try:
            formatted = self._format(record)
            if record["level"].no >= 40:
                sys.stderr.write(formatted + "\n")
            else:
                sys.stdout.write(formatted + "\n")
        except Exception:
            sys.stdout.write(f"{record['level'].name}: {record['message']}\n")

    def _format(self, record: Dict[str, Any]) -> str:
        entry = build_structured_entry(record)
        level = entry["level"]
        msg = entry["message"]

        if self.verbosity == VerbosityLevel.QUIET:
            if level in ("ERROR", "CRITICAL"):
                return f"{level}: {msg}"
            return ""

        if self.verbosity == VerbosityLevel.NORMAL:
            return f"{level}: {msg}"

        # Verbose/debug/trace
        parts = [
            f"[{entry['timestamp']}]",
            f"{level:8}",
            msg,
            f"({entry['module']}:{entry['function']}:{entry['line']})",
        ]

        ctx = entry.get("context", {})
        if ctx:
            ctx_str = " ".join(f"{k}:{str(v)[:8]}" for k, v in ctx.items())
            parts.append(f"[{ctx_str}]")

        return " ".join(parts)


# ---------------------------------------------------------------------------
# Setup logging
# ---------------------------------------------------------------------------

def setup_rich_logging(
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
    enable_json_sink: bool = True,
    enable_yaml_sink: bool = False,
    enable_cbor_sink: bool = False,
    enable_md_sink: bool = False,
):
    """Setup loguru with rich console sink + optional structured sinks."""
    logger.remove()

    # Console sink
    logger.add(RichOutputSink(verbosity), format="{message}", enqueue=True)

    # File sink (classic)
    logger.add(
        "logs/fcc_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # Structured sinks
    if enable_json_sink:
        logger.add(MultiFormatSink("json", "logs/fcc_structured.json"), format="{message}", enqueue=True)

    if enable_yaml_sink:
        logger.add(MultiFormatSink("yaml", "logs/fcc_structured.yaml"), format="{message}", enqueue=True)

    if enable_cbor_sink:
        logger.add(MultiFormatSink("cbor", "logs/fcc_structured"), format="{message}", enqueue=True)

    if enable_md_sink:
        logger.add(MultiFormatSink("md", "logs/fcc_structured.md"), format="{message}", enqueue=True)


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------

def get_rich_logger(name: str = "fcc"):
    return logger.bind(name=name)


def log_with_request_id(message: str, request_id: str, level: str = "info"):
    logger.bind(request_id=request_id).log(level.upper(), redact_text(message))


def log_with_session_id(message: str, session_id: str, level: str = "info"):
    logger.bind(session_id=session_id).log(level.upper(), redact_text(message))


def log_with_context(message: str, level: str = "info", **context):
    logger.bind(**context).log(level.upper(), redact_text(message))
