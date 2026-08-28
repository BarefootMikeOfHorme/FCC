#!/usr/bin/env python3
"""Verification test for rich output formatter (without Unicode characters)."""

import sys
import os
from datetime import datetime, timezone

# Add the src directory to the path so we can import free_claude_code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from free_claude_code.core.output_schemas import (
    VerbosityLevel,
    OutputFormat,
    QueryResponse,
    LogEntry,
)
from free_claude_code.core.rich_output import (
    RichOutputFormatter,
    format_and_print_query,
    format_and_print_log,
    get_rich_formatter
)
from rich.panel import Panel
from rich.text import Text


def test_basic_functionality():
    """Test that basic rich output functionality works."""
    print("Testing basic rich output functionality...")

    # Create a sample query response
    response = QueryResponse(
        response="The capital of France is Paris.",
        model_used="claude-3-5-sonnet-20241022",
        timestamp=datetime.now(timezone.utc).isoformat(),
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

    # Test different verbosity levels produce correct types
    formatter = RichOutputFormatter(VerbosityLevel.QUIET)
    quiet_output = formatter.format_query_response(response, OutputFormat.TEXT)
    assert isinstance(quiet_output, str), "QUIET should return string"
    assert quiet_output == "The capital of France is Paris.", "QUIET output incorrect"
    print("  QUIET formatting: PASS")

    formatter = RichOutputFormatter(VerbosityLevel.NORMAL)
    normal_output = formatter.format_query_response(response, OutputFormat.TEXT)
    # Should return a Panel object for NORMAL verbosity
    assert isinstance(normal_output, Panel), f"NORMAL should return Panel, got {type(normal_output)}"
    print("  NORMAL formatting: PASS")

    formatter = RichOutputFormatter(VerbosityLevel.VERBOSE)
    verbose_output = formatter.format_query_response(response, OutputFormat.TEXT)
    # Should return a Panel object for VERBOSE verbosity
    assert isinstance(verbose_output, Panel), f"VERBOSE should return Panel, got {type(verbose_output)}"
    print("  VERBOSE formatting: PASS")

    # Test JSON format
    json_output = formatter.format_query_response(response, OutputFormat.JSON)
    assert isinstance(json_output, str), "JSON should return string"
    assert '"response": "The capital of France is Paris."' in json_output, "JSON output incorrect"
    print("  JSON formatting: PASS")

    # Test MARKDOWN format
    md_output = formatter.format_query_response(response, OutputFormat.MARKDOWN)
    assert isinstance(md_output, Panel), f"MARKDOWN should return Panel, got {type(md_output)}"
    print("  MARKDOWN formatting: PASS")

    # Test log entry formatting
    log_entry = LogEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        level="INFO",
        message="Processing user query",
        module="messaging.workflow",
        function="process_query",
        line=142,
        request_id="req_123abc",
        session_id="sess_456def",
        metadata={"query_length": 25, "model": "gpt-4"}
    )

    formatter = RichOutputFormatter(VerbosityLevel.QUIET)
    quiet_log = formatter.format_log_entry(log_entry, OutputFormat.TEXT)
    assert isinstance(quiet_log, str), "QUIET log should return string"
    # Should be empty for INFO level in QUIET mode
    assert quiet_log == "", "QUIET log for INFO should be empty"
    print("  QUIET log formatting: PASS")

    formatter = RichOutputFormatter(VerbosityLevel.NORMAL)
    normal_log = formatter.format_log_entry(log_entry, OutputFormat.TEXT)
    # For NORMAL verbosity, we return a Text object for rich formatting
    assert isinstance(normal_log, Text), f"NORMAL log should return Text, got {type(normal_log)}"
    # The Text object should contain the expected content when converted to string
    assert "INFO: Processing user query" in str(normal_log), "NORMAL log output incorrect"
    print("  NORMAL log formatting: PASS")

    formatter = RichOutputFormatter(VerbosityLevel.VERBOSE)
    verbose_log = formatter.format_log_entry(log_entry, OutputFormat.TEXT)
    # For VERBOSE, log entry should return a Panel (based on implementation)
    assert isinstance(verbose_log, Panel), f"VERBOSE log should return Panel, got {type(verbose_log)}"
    print("  VERBOSE log formatting: PASS")

    # Test progress bar creation
    progress = formatter.create_progress_bar("Testing...", total=100)
    assert progress is not None, "Should create progress bar"
    task_id = formatter.start_progress("Testing...", total=100)
    assert task_id is not None, "Should return task ID"
    formatter.update_progress(task_id, advance=10)
    formatter.stop_progress()
    print("  Progress bar functionality: PASS")

    print("All basic functionality tests PASSED")


def test_convenience_functions():
    """Test convenience functions work without errors."""
    print("Testing convenience functions...")

    formatter = get_rich_formatter(VerbosityLevel.NORMAL)

    # These should not raise exceptions
    try:
        formatter.print_banner("Test Title", "Test Subtitle")
        formatter.print_success("Success message")
        formatter.print_warning("Warning message")
        formatter.print_error("Error message")
        formatter.print_info("Info message")
        print("  Convenience functions: PASS")
    except Exception as e:
        print(f"  Convenience functions: FAIL - {e}")
        raise


def main():
    """Run verification tests."""
    print("=" * 50)
    print("Verifying Rich Output Implementation")
    print("=" * 50)

    try:
        test_basic_functionality()
        test_convenience_functions()

        print("=" * 50)
        print("All verification tests PASSED")
        print("Rich output implementation is working correctly")
        print("=" * 50)
        return 0

    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())