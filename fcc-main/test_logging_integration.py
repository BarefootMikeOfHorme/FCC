#!/usr/bin/env python3
"""Test script for logging integration."""

import sys
import os
import tempfile
import shutil

# Add the src directory to the path so we can import free_claude_code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from free_claude_code.core.logging_integration import (
    setup_rich_logging,
    log_with_request_id,
    log_with_session_id,
    log_with_context
)
from free_claude_code.core.output_schemas import VerbosityLevel


def test_logging_setup():
    """Test setting up rich logging."""
    print("Testing logging setup...")

    # Create a temporary directory for logs
    temp_dir = tempfile.mkdtemp()
    try:
        # Setup rich logging
        setup_rich_logging(VerbosityLevel.NORMAL)

        # Import logger after setup
        from loguru import logger

        # Test basic logging
        logger.info("This is an info message")
        logger.warning("This is a warning message")
        logger.error("This is an error message")

        # Test that our sinks were added
        assert len(logger._core.handlers) > 0, "Should have logging handlers"

        print("  Logging setup test PASSED")
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_contextual_logging():
    """Test logging with contextual information."""
    print("Testing contextual logging...")

    # Setup rich logging
    setup_rich_logging(VerbosityLevel.NORMAL)

    from loguru import logger

    # Capture log output by adding a string sink
    from io import StringIO
    log_stream = StringIO()
    logger.add(log_stream, format="{message}", enqueue=False)

    # Test request ID logging
    log_with_request_id("Processing request", "req_123abc", "info")
    log_output = log_stream.getvalue()
    assert "Processing request" in log_output, "Message should be in log output"
    # Note: The exact format depends on our RichOutputSink implementation

    # Reset stream
    log_stream.seek(0)
    log_stream.truncate(0)

    # Test session ID logging
    log_with_session_id("User login", "sess_456def", "info")
    log_output = log_stream.getvalue()
    assert "User login" in log_output, "Message should be in log output"

    # Reset stream
    log_stream.seek(0)
    log_stream.truncate(0)

    # Test general context logging
    log_with_context("Database query executed", query="SELECT * FROM users", rows=10, level="debug")
    log_output = log_stream.getvalue()
    assert "Database query executed" in log_output, "Message should be in log output"

    print("  Contextual logging test PASSED")


def test_different_verbosity_levels():
    """Test logging with different verbosity levels."""
    print("Testing different verbosity levels...")

    from loguru import logger

    # Test QUIET verbosity
    setup_rich_logging(VerbosityLevel.QUIET)
    from io import StringIO
    log_stream = StringIO()
    logger.add(log_stream, format="{message}", enqueue=False)

    logger.info("Info message in quiet mode")  # Should not appear
    logger.error("Error message in quiet mode")  # Should appear
    log_output = log_stream.getvalue()
    assert "Info message in quiet mode" not in log_output, "Info should not appear in quiet mode"
    assert "Error message in quiet mode" in log_output, "Error should appear in quiet mode"

    # Reset for next test
    logger.remove()
    log_stream.seek(0)
    log_stream.truncate(0)

    # Test NORMAL verbosity
    setup_rich_logging(VerbosityLevel.NORMAL)
    logger.add(log_stream, format="{message}", enqueue=False)

    logger.info("Info message in normal mode")
    logger.error("Error message in normal mode")
    log_output = log_stream.getvalue()
    assert "Info message in normal mode" in log_output, "Info should appear in normal mode"
    assert "Error message in normal mode" in log_output, "Error should appear in normal mode"

    print("  Different verbosity levels test PASSED")


def main():
    """Run all tests."""
    print("=" * 50)
    print("Testing Logging Integration")
    print("=" * 50)

    try:
        test_logging_setup()
        test_contextual_logging()
        test_different_verbosity_levels()

        print("=" * 50)
        print("All logging integration tests PASSED")
        print("=" * 50)
        return 0

    except Exception as e:
        print(f"Testing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())