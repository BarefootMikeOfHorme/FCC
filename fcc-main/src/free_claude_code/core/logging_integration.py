"""Enhanced logging integration for Free Claude Code.

Supports:
- TEXT, JSON, JSONC, YAML, YAML-C, MD, HTML, CBOR
- Rich console sink
- Structured sinks
- Redaction layer
- Context-aware logging
"""

from __future__ import annotations

import sys
import json
import re
from typing import Any, Dict

from loguru import logger

from .output_schemas import VerbosityLevel, OutputFormat, LogEntry, format_log_entry
from .json_types import ensure_json_safe, dump_any, JsonError

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
    sanitized = text
    for pattern, replacement in _SECRET_REPLACEMENTS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


# ---------------------------------------------------------------------------
# Structured log entry builder
# ---------------------------------------------------------------------------

def build_structured_entry(record: Dict[str, Any]) -> LogEntry:
    entry_dict = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": redact_text(record["message"]),
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
    }

    extra = record.get("extra", {})
    if extra:
        entry_dict["metadata"] = dict(extra)

    return LogEntry.model_validate(entry_dict)


# ---------------------------------------------------------------------------
# Multi-format sinks
# ---------------------------------------------------------------------------

class MultiFormatSink:
    """Writes logs in JSON, JSONC, YAML, YAML-C, HTML, CBOR."""

    def __init__(self, format: OutputFormat, path: str):
        self.format = format
        self.path = path

    def __call__(self, message):
        record = message.record
        entry = build_structured_entry(record)
        safe_entry = ensure_json_safe(entry.model_dump())

        try:
            if self.format == OutputFormat.JSON:
                text = dump_any(safe_entry, format="json")

            elif self.format == OutputFormat.JSONC:
                text = "// JSONC\n" + dump_any(safe_entry, format="json")

            elif self.format == OutputFormat.YAML:
                if yaml is None:
                    return
                text = yaml.dump(safe_entry, sort_keys=False)

            elif self.format == OutputFormat.YAMLC:
                if yaml is None:
                    return
                text = "# YAML-C\n" + yaml.dump(safe_entry, sort_keys=False)

            elif self.format == OutputFormat.HTML:
                text = f"<pre>{dump_any(safe_entry, format='json')}</pre>"

            elif self.format == OutputFormat.CBOR:
                if cbor2 is None:
                    return
                data = cbor2.dumps(safe_entry)
                with open(self.path + ".cbor", "ab") as f:
                    f.write(data)
                return

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
    """Outputs logs to console using rich formatting."""

    def __init__(self, verbosity: VerbosityLevel = VerbosityLevel.NORMAL):
        self.verbosity = verbosity

    def __call__(self, message):
        record = message.record
        try:
            entry = build_structured_entry(record)
            formatted = format_log_entry(entry, self.verbosity, OutputFormat.TEXT)
            if record["level"].no >= 40:
                sys.stderr.write(formatted + "\n")
            else:
                sys.stdout.write(formatted + "\n")
        except Exception:
            sys.stdout.write(f"{record['level'].name}: {record['message']}\n")


# ---------------------------------------------------------------------------
# Setup logging
# ---------------------------------------------------------------------------

def setup_rich_logging(
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
    enable_json_sink: bool = True,
    enable_jsonc_sink: bool = False,
    enable_yaml_sink: bool = False,
    enable_yamlc_sink: bool = False,
    enable_html_sink: bool = False,
    enable_cbor_sink: bool = False,
):
    logger.remove()

    # Console sink
    logger.add(RichOutputSink(verbosity), format="{message}", enqueue=True)

    # Classic file sink
    logger.add(
        "logs/fcc_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # Structured sinks
    if enable_json_sink:
        logger.add(
            MultiFormatSink(OutputFormat.JSON, "logs/fcc_structured.json"),
            format="{message}",
            enqueue=True,
        )

    if enable_jsonc_sink:
        logger.add(
            MultiFormatSink(OutputFormat.JSONC, "logs/fcc_structured.jsonc"),
            format="{message}",
            enqueue=True,
        )

    if enable_yaml_sink:
        logger.add(
            MultiFormatSink(OutputFormat.YAML, "logs/fcc_structured.yaml"),
            format="{message}",
            enqueue=True,
        )

    if enable_yamlc_sink:
        logger.add(
            MultiFormatSink(OutputFormat.YAMLC, "logs/fcc_structured.yamlc"),
            format="{message}",
            enqueue=True,
        )

    if enable_html_sink:
        logger.add(
            MultiFormatSink(OutputFormat.HTML, "logs/fcc_structured.html"),
            format="{message}",
            enqueue=True,
        )

    if enable_cbor_sink:
        logger.add(
            MultiFormatSink(OutputFormat.CBOR, "logs/fcc_structured"),
            format="{message}",
            enqueue=True,
        )


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
