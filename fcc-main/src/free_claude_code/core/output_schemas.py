"""Output format schemas for Free Claude Code.

Enhanced version:
- Supports TEXT, JSON, JSONC, YAML, YAML-C, MD, HTML, CBOR
- Adds extended metric types
- Provides complete formatters for QueryResponse and LogEntry
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict

# Optional format libraries
try:
    import yaml
except Exception:
    yaml = None

try:
    import cbor2
except Exception:
    cbor2 = None


# ============ ENUMS ============

class VerbosityLevel(StrEnum):
    QUIET = "quiet"
    NORMAL = "normal"
    VERBOSE = "verbose"
    DEBUG = "debug"
    TRACE = "trace"


class OutputFormat(StrEnum):
    TEXT = "text"
    JSON = "json"
    JSONC = "jsonc"
    YAML = "yaml"
    YAMLC = "yamlc"
    MARKDOWN = "md"
    HTML = "html"
    CBOR = "cbor"


class MetricType(StrEnum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"
    PERCENT = "percent"
    BYTES = "bytes"
    EVENTS = "events"


# ============ BASE OUTPUT SCHEMA ============

@dataclass
class OutputSchema:
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL
    format: OutputFormat = OutputFormat.TEXT
    request_id: Optional[str] = None
    session_id: Optional[str] = None


# ============ QUERY OUTPUT SCHEMAS ============

class QueryResponse(BaseModel):
    response: str = Field(...)
    model_used: str = Field(...)

    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    request_id: Optional[str] = Field(None)
    session_id: Optional[str] = Field(None)

    prompt_tokens: Optional[int] = Field(None)
    completion_tokens: Optional[int] = Field(None)
    total_tokens: Optional[int] = Field(None)

    latency_ms: Optional[float] = Field(None)
    time_to_first_token: Optional[float] = Field(None)

    safety_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore", frozen=True, validate_assignment=True)


class StreamChunk(BaseModel):
    delta: str = Field(...)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    request_id: Optional[str] = Field(None)
    session_id: Optional[str] = Field(None)
    is_final: bool = Field(False)

    prompt_tokens: Optional[int] = Field(None)
    completion_tokens: Optional[int] = Field(None)
    total_tokens: Optional[int] = Field(None)

    model_config = ConfigDict(extra="ignore")


# ============ LOG OUTPUT SCHEMAS ============

class LogEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    level: str = Field(...)
    message: str = Field(...)

    module: str = Field(...)
    function: str = Field(...)
    line: int = Field(...)

    request_id: Optional[str] = Field(None)
    session_id: Optional[str] = Field(None)
    node_id: Optional[str] = Field(None)
    chat_id: Optional[str] = Field(None)

    event_type: Optional[str] = Field(None)
    user_id: Optional[str] = Field(None)
    source_ip: Optional[str] = Field(None)
    action_taken: Optional[str] = Field(None)
    outcome: Optional[str] = Field(None)

    trace_payload: Optional[Dict[str, Any]] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class SecurityAuditLogEntry(LogEntry):
    security_level: str = Field(...)
    event_type: str = Field(...)

    signature: str = Field(...)
    previous_signature: Optional[str] = Field(None)

    resource_accessed: Optional[str] = Field(None)
    additional_data: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


# ============ METRICS AND MONITORING SCHEMAS ============

class MetricPoint(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metric_name: str = Field(...)
    metric_type: MetricType = Field(...)
    value: Union[int, float] = Field(...)
    tags: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class SystemMetrics(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    avg_latency_ms: Optional[float] = Field(None)
    p95_latency_ms: Optional[float] = Field(None)
    p99_latency_ms: Optional[float] = Field(None)
    requests_per_second: Optional[float] = Field(None)

    cpu_usage_percent: Optional[float] = Field(None)
    memory_usage_mb: Optional[float] = Field(None)
    memory_usage_percent: Optional[float] = Field(None)
    disk_usage_percent: Optional[float] = Field(None)

    active_sessions: Optional[int] = Field(None)
    total_requests: Optional[int] = Field(None)
    error_rate: Optional[float] = Field(None)

    model_usage: Dict[str, int] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


# ============ PROGRESS AND STATUS SCHEMAS ============

class ProgressUpdate(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    operation_id: str = Field(...)
    operation_name: str = Field(...)

    percentage: float = Field(..., ge=0.0, le=100.0)
    current_step: Optional[str] = Field(None)
    total_steps: Optional[int] = Field(None)
    completed_steps: Optional[int] = Field(None)

    elapsed_seconds: Optional[float] = Field(None)
    estimated_remaining_seconds: Optional[float] = Field(None)
    estimated_total_seconds: Optional[float] = Field(None)

    status: str = Field("running")
    message: Optional[str] = Field(None)

    model_config = ConfigDict(extra="ignore")


# ============ OUTPUT FORMATTERS ============

def _jsonc(obj: Any) -> str:
    """JSON-with-comments (JSONC)"""
    import json
    return "// JSONC\n" + json.dumps(obj, indent=2)


def _yaml(obj: Any) -> str:
    if yaml is None:
        return "YAML unavailable"
    return yaml.dump(obj, sort_keys=False)


def _yamlc(obj: Any) -> str:
    if yaml is None:
        return "YAML unavailable"
    return "# YAML-C\n" + yaml.dump(obj, sort_keys=False)


def _html_pre(text: str) -> str:
    return f"<pre>{text}</pre>"


def _cbor(obj: Any) -> bytes:
    if cbor2 is None:
        return b""
    return cbor2.dumps(obj)


# ---------------- QUERY RESPONSE FORMATTER ----------------

def format_query_response(
    response: QueryResponse,
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
    fmt: OutputFormat = OutputFormat.TEXT,
) -> Union[str, bytes]:
    obj = response.model_dump()

    if fmt == OutputFormat.JSON:
        return response.model_dump_json(indent=2)

    if fmt == OutputFormat.JSONC:
        return _jsonc(obj)

    if fmt == OutputFormat.YAML:
        return _yaml(obj)

    if fmt == OutputFormat.YAMLC:
        return _yamlc(obj)

    if fmt == OutputFormat.MARKDOWN:
        return f"# Claude Response\n\n{response.response}\n\n**Model:** {response.model_used}"

    if fmt == OutputFormat.HTML:
        return _html_pre(response.response)

    if fmt == OutputFormat.CBOR:
        return _cbor(obj)

    # TEXT
    if verbosity == VerbosityLevel.QUIET:
        return response.response

    if verbosity == VerbosityLevel.NORMAL:
        return response.response

    # VERBOSE / DEBUG / TRACE
    return (
        f"{response.response}\n\n"
        f"Model: {response.model_used}\n"
        f"Time: {response.timestamp}\n"
        f"Latency: {response.latency_ms}\n"
        f"Tokens: {response.total_tokens}\n"
    )


# ---------------- LOG ENTRY FORMATTER ----------------

def format_log_entry(
    entry: LogEntry,
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
    fmt: OutputFormat = OutputFormat.TEXT,
) -> Union[str, bytes]:
    obj = entry.model_dump()

    if fmt == OutputFormat.JSON:
        return entry.model_dump_json(indent=2)

    if fmt == OutputFormat.JSONC:
        return _jsonc(obj)

    if fmt == OutputFormat.YAML:
        return _yaml(obj)

    if fmt == OutputFormat.YAMLC:
        return _yamlc(obj)

    if fmt == OutputFormat.MARKDOWN:
        return (
            f"## Log Entry\n"
            f"- **Timestamp:** {entry.timestamp}\n"
            f"- **Level:** {entry.level}\n"
            f"- **Message:** {entry.message}\n"
            f"- **Source:** {entry.module}:{entry.function}:{entry.line}\n"
        )

    if fmt == OutputFormat.HTML:
        return _html_pre(f"{entry.level}: {entry.message}")

    if fmt == OutputFormat.CBOR:
        return _cbor(obj)

    # TEXT
    if verbosity == VerbosityLevel.QUIET:
        if entry.level in ("ERROR", "CRITICAL"):
            return f"{entry.level}: {entry.message}"
        return ""

    if verbosity == VerbosityLevel.NORMAL:
        return f"{entry.level}: {entry.message}"

    # VERBOSE / DEBUG / TRACE
    return (
        f"[{entry.timestamp}] {entry.level}: {entry.message} "
        f"({entry.module}:{entry.function}:{entry.line})"
    )


# ============ SCHEMA REGISTRY ============

SCHEMA_REGISTRY = {
    "query_response": QueryResponse,
    "stream_chunk": StreamChunk,
    "log_entry": LogEntry,
    "security_audit_log_entry": SecurityAuditLogEntry,
    "metric_point": MetricPoint,
    "system_metrics": SystemMetrics,
    "progress_update": ProgressUpdate,
}


def get_schema(name: str):
    return SCHEMA_REGISTRY.get(name)


def list_schemas() -> List[str]:
    return list(SCHEMA_REGISTRY.keys())
