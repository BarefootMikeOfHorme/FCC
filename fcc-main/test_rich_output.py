#!/usr/bin/env python3
"""Test script for rich output formatter."""

import sys
import os
from datetime import datetime

# Add the src directory to the path so we can import free_claude_code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from free_claude_code.core.output_schemas import (
    VerbosityLevel,
    OutputFormat,
    QueryResponse,
    LogEntry,
    SecurityAuditLogEntry,
    MetricPoint,
    SystemMetrics,
    ProgressUpdate,
)
from free_claude_code.core.rich_output import (
    RichOutputFormatter,
    format_and_print_query,
    format_and_print_log,
    get_rich_formatter
)


def test_query_response_formatting():
    """Test formatting of query responses."""
    print("Testing query response formatting...")

    # Create a sample query response
    response = QueryResponse(
        response="The capital of France is Paris.",
        model_used="claude-3-5-sonnet-20241022",
        timestamp=datetime.utcnow().isoformat() + "Z",
        request_id="req_123abc",
        session_id="sess_456def",
        prompt_tokens=15,
        completion_tokens=8,
        total_tokens=23,
        latency_ms=1250.5,
        time_to_first_token=350.2,
        safety_score=0.98,
        relevance_score=0.95,
        metadata={"temperature": 0.7, "max_tokens": 100}
    )

    # Test different verbosity levels
    formatter = RichOutputFormatter(VerbosityLevel.QUIET)
    quiet_output = formatter.format_query_response(response, OutputFormat.TEXT)
    print(f"QUIET output: '{quiet_output}'")

    formatter = RichOutputFormatter(VerbosityLevel.NORMAL)
    normal_output = formatter.format_query_response(response, OutputFormat.TEXT)
    print(f"NORMAL output type: {type(normal_output)}")

    formatter = RichOutputFormatter(VerbosityLevel.VERBOSE)
    verbose_output = formatter.format_query_response(response, OutputFormat.TEXT)
    print(f"VERBOSE output type: {type(verbose_output)}")

    # Test JSON format
    json_output = formatter.format_query_response(response, OutputFormat.JSON)
    print(f"JSON output type: {type(json_output)}")
    print(f"JSON output starts with: {json_output[:100]}...")

    # Test MARKDOWN format
    md_output = formatter.format_query_response(response, OutputFormat.MARKDOWN)
    print(f"MARKDOWN output type: {type(md_output)}")

    print("✓ Query response formatting tests passed\n")


def test_log_entry_formatting():
    """Test formatting of log entries."""
    print("Testing log entry formatting...")

    # Create a sample log entry
    log_entry = LogEntry(
        timestamp=datetime.utcnow().isoformat() + "Z",
        level="INFO",
        message="Processing user query",
        module="messaging.workflow",
        function="process_query",
        line=142,
        request_id="req_123abc",
        session_id="sess_456def",
        metadata={"query_length": 25, "model": "gpt-4"}
    )

    # Test different verbosity levels
    formatter = RichOutputFormatter(VerbosityLevel.QUIET)
    quiet_output = formatter.format_log_entry(log_entry, OutputFormat.TEXT)
    print(f"QUIET log output: '{quiet_output}'")

    formatter = RichOutputFormatter(VerbosityLevel.NORMAL)
    normal_output = formatter.format_log_entry(log_entry, OutputFormat.TEXT)
    print(f"NORMAL log output type: {type(normal_output)}")

    formatter = RichOutputFormatter(VerbosityLevel.VERBOSE)
    verbose_output = formatter.format_log_entry(log_entry, OutputFormat.TEXT)
    print(f"VERBOSE log output type: {type(verbose_output)}")

    # Test security audit log entry
    security_entry = SecurityAuditLogEntry(
        timestamp=datetime.utcnow().isoformat() + "Z",
        level="SECURITY",
        message="Authentication failed for user",
        module="security_audit",
        function="log_authentication_event",
        line=87,
        request_id="req_123abc",
        user_id="test_user",
        source_ip="192.168.1.100",
        security_level="medium",
        event_type="authentication",
        action_taken="authenticate_via_password",
        outcome="failure",
        signature="a1b2c3d4e5f6...",
        previous_signature="f6e5d4c3b2a1...",
        additional_data={
            "authentication_method": "password",
            "failure_reason": "invalid_credentials"
        }
    )

    formatter = RichOutputFormatter(VerbosityLevel.VERBOSE)
    security_output = formatter.format_log_entry(security_entry, OutputFormat.TEXT)
    print(f"Security log output type: {type(security_output)}")

    print("✓ Log entry formatting tests passed\n")


def test_progress_bars():
    """Test progress bar functionality."""
    print("Testing progress bar functionality...")

    formatter = RichOutputFormatter(VerbosityLevel.NORMAL)

    # Test creating and using progress bar
    progress = formatter.create_progress_bar("Testing progress...", total=100)
    task_id = formatter.start_progress("Testing progress...", total=100)

    # Simulate some progress
    for i in range(0, 101, 10):
        formatter.update_progress(task_id, advance=10, description=f"Processing step {i}%")
        # In a real scenario, we'd have some delay here

    formatter.stop_progress()
    print("✓ Progress bar tests passed\n")


def test_metrics_display():
    """Test metrics display functionality."""
    print("Testing metrics display...")

    formatter = RichOutputFormatter(VerbosityLevel.NORMAL)

    # Create sample metrics
    metrics = SystemMetrics(
        timestamp=datetime.utcnow().isoformat() + "Z",
        avg_latency_ms=1250.5,
        p95_latency_ms=2100.0,
        p99_latency_ms=3500.0,
        requests_per_second=12.5,
        cpu_usage_percent=45.2,
        memory_usage_mb=512.0,
        memory_usage_percent=62.8,
        disk_usage_percent=23.1,
        active_sessions=8,
        total_requests=1245,
        error_rate=0.02,
        model_usage={
            "gpt-4": 450,
            "claude-3": 320,
            "llama-2": 180,
            "mixtral": 120,
            "gemini-pro": 175
        }
    )

    # This would normally print to console, but we'll just verify it doesn't crash
    formatter.display_metrics(metrics)
    print("✓ Metrics display tests passed\n")


def test_progress_updates():
    """Test progress update display."""
    print("Testing progress update display...")

    formatter = RichOutputFormatter(VerbosityLevel.NORMAL)

    # Create sample progress update
    update = ProgressUpdate(
        timestamp=datetime.utcnow().isoformat() + "Z",
        operation_id="op_789xyz",
        operation_name="Processing document batch",
        percentage=65.5,
        current_step="Embedding generation",
        total_steps=10,
        completed_steps=6,
        elapsed_seconds=45.2,
        estimated_remaining_seconds=23.8,
        estimated_total_seconds=69.0,
        status="running",
        message="Processing step 7 of 10"
    )

    formatter.display_progress_update(update)
    print("✓ Progress update tests passed\n")


def test_convenience_functions():
    """Test convenience functions."""
    print("Testing convenience functions...")

    formatter = get_rich_formatter(VerbosityLevel.NORMAL)

    # Test banner
    formatter.print_banner("Free Claude Code", "Enhanced AI Assistant")

    # Test status messages
    formatter.print_success("Operation completed successfully")
    formatter.print_warning("This is a warning message")
    formatter.print_error("An error occurred")
    formatter.print_info("This is informational")

    print("✓ Convenience function tests passed\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Rich Output Formatter")
    print("=" * 60)

    try:
        test_query_response_formatting()
        test_log_entry_formatting()
        test_progress_bars()
        test_metrics_display()
        test_progress_updates()
        test_convenience_functions()

        print("=" * 60)
        print("All tests passed! 🎉")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())