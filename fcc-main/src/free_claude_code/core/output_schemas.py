"""Output format schemas for Free Claude Code.

This module defines standardized schemas for different output formats and verbosity levels
to enable rich terminals, monitoring, and consistent UI experiences.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


# ============ ENUMS ============

class VerbosityLevel(StrEnum):
    """Verbosity levels for output formatting."""
    QUIET = "quiet"
    NORMAL = "normal"
    VERBOSE = "verbose"
    DEBUG = "debug"
    TRACE = "trace"


class OutputFormat(StrEnum):
    """Supported output formats."""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "md"
    HTML = "html"


class MetricType(StrEnum):
    """Types of metrics that can be monitored."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


# ============ BASE OUTPUT SCHEMA ============

@dataclass
class OutputSchema:
    """Base schema for all output formats."""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL
    format: OutputFormat = OutputFormat.TEXT
    request_id: Optional[str] = None
    session_id: Optional[str] = None


# ============ QUERY OUTPUT SCHEMAS ============

class QueryResponse(BaseModel):
    """Schema for standard query responses."""
    response: str = Field(..., description="The main response text")
    model_used: str = Field(..., description="Identifier of the model that generated the response")

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

    class Config:
        json_schema_extra = {
            "example": {
                "response": "The capital of France is Paris.",
                "model_used": "gpt-4",
                "timestamp": "2026-08-24T20:46:53.123Z",
                "request_id": "req_123abc",
                "session_id": "sess_456def",
                "prompt_tokens": 15,
                "completion_tokens": 8,
                "total_tokens": 23,
                "latency_ms": 1250.5,
                "time_to_first_token": 350.2,
                "safety_score": 0.98,
                "relevance_score": 0.95,
                "metadata": {"temperature": 0.7, "max_tokens": 100}
            }
        }


class StreamChunk(BaseModel):
    """Schema for streaming response chunks."""
    delta: str = Field(...)

    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    request_id: Optional[str] = Field(None)
    session_id: Optional[str] = Field(None)
    is_final: bool = Field(False)

    prompt_tokens: Optional[int] = Field(None)
    completion_tokens: Optional[int] = Field(None)
    total_tokens: Optional[int] = Field(None)

    class Config:
        json_schema_extra = {
            "example": {
                "delta": " Paris.",
                "timestamp": "2026-08-24T20:46:53.456Z",
                "request_id": "req_123abc",
                "session_id": "sess_456def",
                "is_final": True,
                "prompt_tokens": 15,
                "completion_tokens": 8,
                "total_tokens": 23
            }
        }


# ============ LOG OUTPUT SCHEMAS ============

class LogEntry(BaseModel):
    """Schema for structured log entries."""
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

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-08-24T20:46:53.123Z",
                "level": "INFO",
                "message": "Processing user query",
                "module": "messaging.workflow",
                "function": "process_query",
                "line": 142,
                "request_id": "req_123abc",
                "session_id": "sess_456def",
                "metadata": {"query_length": 25, "model": "gpt-4"}
            }
        }


class SecurityAuditLogEntry(LogEntry):
    """Schema for security audit log entries with cryptographic chaining."""
    security_level: str = Field(...)
    event_type: str = Field(...)

    signature: str = Field(...)
    previous_signature: Optional[str] = Field(None)

    resource_accessed: Optional[str] = Field(None)
    additional_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-08-24T20:46:53.123Z",
                "level": "SECURITY",
                "message": "Authentication failed for user",
                "module": "security_audit",
                "function": "log_authentication_event",
                "line": 87,
                "request_id": "req_123abc",
                "user_id": "test_user",
                "source_ip": "192.168.1.100",
                "security_level": "medium",
                "event_type": "authentication",
                "action_taken": "authenticate_via_password",
                "outcome": "failure",
                "signature": "a1b2c3d4e5f6...",
                "previous_signature": "f6e5d4c3b2a1...",
                "additional_data": {
                    "authentication_method": "password",
                    "failure_reason": "invalid_credentials"
                }
            }
        }


# ============ METRICS AND MONITORING SCHEMAS ============

class MetricPoint(BaseModel):
    """Schema for a single metric measurement."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    metric_name: str = Field(...)
    metric_type: MetricType = Field(...)
    value: Union[int, float] = Field(...)
    tags: Dict[str, str] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-08-24T20:46:53.123Z",
                "metric_name": "request_latency_ms",
                "metric_type": "histogram",
                "value": 1250.5,
                "tags": {
                    "endpoint": "/query",
                    "model": "gpt-4",
                    "status": "success"
                }
            }
        }


class SystemMetrics(BaseModel):
    """Schema for system-wide metrics snapshot."""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    avg_latency_ms: Optional[float] = Field(None)
    p95_latency_ms: Optional[float] = Field(None)
    p99_latency_ms: Optional[float] = Field(None)
    requests_per_second: Optional[float] = Field(None)

    cpu_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    memory_usage_mb: Optional[float] = Field(None)
    memory_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    disk_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0)

    active_sessions: Optional[int] = Field(None)
    total_requests: Optional[int] = Field(None)
    error_rate: Optional[float] = Field(None, ge=0.0, le=1.0)

    model_usage: Dict[str, int] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-08-24T20:46:53.123Z",
                "avg_latency_ms": 1250.5,
                "p95_latency_ms": 2100.0,
                "p99_latency_ms": 3500.0,
                "requests_per_second": 12.5,
                "cpu_usage_percent": 45.2,
                "memory_usage_mb": 512.0,
                "memory_usage_percent": 62.8,
                "disk_usage_percent": 23.1,
                "active_sessions": 8,
                "total_requests": 1245,
                "error_rate": 0.02,
                "model_usage": {
                    "gpt-4": 450,
                    "claude-3": 320,
                    "llama-2": 180,
                    "mixtral": 120,
                    "gemini-pro": 175
                }
            }
        }


# ============ PROGRESS AND STATUS SCHEMAS ============

class ProgressUpdate(BaseModel):
    """Schema for progress updates during long-running operations."""
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

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-08-24T20:46:53.123Z",
                "operation_id": "op_789xyz",
                "operation_name": "Processing document batch",
                "percentage": 65.5,
                "current_step": "Embedding generation",
                "total_steps": 10,
                "completed_steps": 6,
                "elapsed_seconds": 45.2,
                "estimated_remaining_seconds": 23.8,
                "estimated_total_seconds": 69.0,
                "status": "running",
                "message": "Processing step 7 of 10"
            }
        }


# ============ OUTPUT FORMATTERS ============

def format_query_response(
    response: QueryResponse,
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
    fmt: OutputFormat = OutputFormat.TEXT
) -> str:
    """Format a query response according to verbosity and format preferences."""
    if fmt == OutputFormat.JSON:
        return response.model_dump_json(
            indent=2 if verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG) else None
        )

    elif fmt == OutputFormat.MARKDOWN:
        md = f"""# Response

{response.response}

## Metadata
- **Model**: {response.model_used}
- **Timestamp**: {response.timestamp}
"""
        if response.request_id:
            md += f"- **Request ID**: {response.request_id}\n"
        if response.session_id:
            md += f"- **Session ID**: {response.session_id}\n"

        if verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG):
            md += f"""## Token Usage
- **Prompt Tokens**: {response.prompt_tokens or 0}
- **Completion Tokens**: {response.completion_tokens or 0}
- **Total Tokens**: {response.total_tokens or 0}

## Performance
- **Latency**: {response.latency_ms or 0:.1f}ms
- **Time to First Token**: {response.time_to_first_token or 0:.1f}ms

## Quality Scores
- **Safety**: {response.safety_score or 0:.2f}
- **Relevance**: {response.relevance_score or 0:.2f}
"""

            if response.metadata:
                md += "## Additional Metadata\n"
                for key, value in response.metadata.items():
                    md += f"- **{key}**: {value}\n"

        return md

    else:  # TEXT format
        if verbosity == VerbosityLevel.QUIET:
            return response.response

        elif verbosity == VerbosityLevel.NORMAL:
            lines = [response.response]
            if response.latency_ms:
                lines.append(f"[{response.latency_ms:.0f}ms]")
            return "\n".join(lines)

        else:  # VERBOSE, DEBUG, TRACE
            lines = [
                response.response,
                "",
                f"Model: {response.model_used}",
                f"Time: {response.timestamp}",
            ]

            if response.request_id:
                lines.append(f"Request ID: {response.request_id}")
            if response.session_id:
                lines.append(f"Session ID: {response.session_id}")

            if verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG):
                lines.extend([
                    "",
                    "Token Usage:",
                    f"  Prompt: {response.prompt_tokens or 0}",
                    f"  Completion: {response.completion_tokens or 0}",
                    f"  Total: {response.total_tokens or 0}",
                    "",
                    "Performance:",
                    f"  Latency: {response.latency_ms or 0:.1f}ms",
                    f"  Time to First Token: {response.time_to_first_token or 0:.1f}ms",
                    "",
                    "Quality Scores:",
                    f"  Safety: {response.safety_score or 0:.2f}",
                    f"  Relevance: {response.relevance_score or 0:.2f}",
                ])

                if response.metadata:
                    lines.extend(["", "Additional Metadata:"])
                    for key, value in response.metadata.items():
                        lines.append(f"  {key}: {value}")

            return "\n".join(lines)


def format_log_entry(
    entry: LogEntry,
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
    fmt: OutputFormat = OutputFormat.TEXT
) -> str:
    """Format a log entry according to verbosity and format preferences."""
    if fmt == OutputFormat.JSON:
        return entry.model_dump_json(
            indent=2 if verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG) else None
        )

    elif fmt == OutputFormat.MARKDOWN:
        md = f"""## Log Entry
- **Timestamp**: {entry.timestamp}
- **Level**: {entry.level}
- **Message**: {entry.message}

**Source**: {entry.module}:{entry.function}:{entry.line}
"""
        if entry.request_id:
            md += f"- **Request ID**: {entry.request_id}\n"
        if entry.session_id:
            md += f"- **Session ID**: {entry.session_id}\n"

        if isinstance(entry, SecurityAuditLogEntry):
            md += f"""**Security Info**:
- **Security Level**: {entry.security_level}
- **Event Type**: {entry.event_type}
- **Action Taken**: {entry.action_taken}
- **Outcome**: {entry.outcome}
"""
            if entry.source_ip:
                md += f"- **Source IP**: {entry.source_ip}\n"

        if verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG) and entry.metadata:
            md += "\n**Metadata**:\n"
            for key, value in entry.metadata.items():
                md += f"- {key}: {value}\n"

        return md

    else:  # TEXT format
        if verbosity == VerbosityLevel.QUIET:
            if entry.level in ("ERROR", "CRITICAL"):
                return f"{entry.level}: {entry.message}"
            return ""

        elif verbosity == VerbosityLevel.NORMAL:
            return f"{entry.level}: {entry.message}"

        else:  # VERBOSE, DEBUG, TRACE
            parts = [
                f"[{entry.timestamp}]",
                f"{entry.level:8}",
                f"{entry.message}",
                f"({entry.module}:{entry.function}:{entry.line})"
            ]

            context_parts = []
            if entry.request_id:
                context_parts.append(f"req:{entry.request_id[:8]}")
            if entry.session_id:
                context_parts.append(f"sess:{entry.session_id[:8]}")

            if context_parts:
                parts.append(f"[{' '.join(context_parts)}]")

            if verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG) and entry.metadata:
                metadata_str = ", ".join(f"{k}={v}" for k, v in entry.metadata.items())
                parts.append(f"[{metadata_str}]")

            return " ".join(parts)


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

def get_schema(schema_name: str) -> Optional[type[BaseModel]]:
    """Get a schema class by name."""
    return SCHEMA_REGISTRY.get(schema_name)

def list_schemas() -> List[str]:
    """List all available schema names."""
    return list(SCHEMA_REGISTRY.keys())
