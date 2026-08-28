#!/usr/bin/env python3
"""Test script for monitoring components."""

import sys
import os
import time
from datetime import datetime

# Add the src directory to the path so we can import free_claude_code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from free_claude_code.core.monitoring import (
    MetricsCollector,
    MonitoringDashboard,
    get_metrics_collector,
    record_latency,
    record_error,
    record_model_usage
)
from free_claude_code.core.output_schemas import SystemMetrics


def test_metrics_collector():
    """Test the metrics collector functionality."""
    print("Testing metrics collector...")

    collector = MetricsCollector()

    # Test recording latency
    collector.record_latency(100.5)
    collector.record_latency(150.2)
    collector.record_latency(200.8)

    # Test recording errors
    collector.record_error()
    collector.record_error()

    # Test recording model usage
    collector.record_model_usage("gpt-4")
    collector.record_model_usage("claude-3")
    collector.record_model_usage("gpt-4")

    # Test setting active sessions
    collector.set_active_sessions(5)

    # Get current metrics
    metrics = collector.get_current_metrics()

    assert isinstance(metrics, SystemMetrics), "Should return SystemMetrics object"
    assert metrics.total_requests == 3, f"Expected 3 requests, got {metrics.total_requests}"
    assert metrics.error_rate == 2/3, f"Expected error rate 0.667, got {metrics.error_rate}"
    assert metrics.model_usage.get("gpt-4") == 2, f"Expected gpt-4 usage 2, got {metrics.model_usage.get('gpt-4')}"
    assert metrics.active_sessions == 5, f"Expected 5 active sessions, got {metrics.active_sessions}"

    # Test latency calculations
    assert metrics.avg_latency_ms is not None, "Average latency should not be None"
    assert 100 <= metrics.avg_latency_ms <= 200, f"Average latency should be between 100-200ms, got {metrics.avg_latency_ms}"

    print("  Metrics collector tests PASSED")


def test_convenience_functions():
    """Test convenience functions."""
    print("Testing convenience functions...")

    # Reset collector by creating a new one (in real usage, this would be the global instance)
    import free_claude_code.core.monitoring as monitoring_module
    monitoring_module._metrics_collector = None

    # Test convenience functions
    record_latency(75.5)
    record_latency(125.3)
    record_error()
    record_model_usage("test-model")

    collector = get_metrics_collector()
    metrics = collector.get_current_metrics()

    assert metrics.total_requests == 2, f"Expected 2 requests, got {metrics.total_requests}"
    assert metrics.error_rate == 0.5, f"Expected error rate 0.5, got {metrics.error_rate}"
    assert metrics.model_usage.get("test-model") == 1, f"Expected test-model usage 1, got {metrics.model_usage.get('test-model')}"

    print("  Convenience function tests PASSED")


def test_monitoring_dashboard_creation():
    """Test that the monitoring dashboard can be created."""
    print("Testing monitoring dashboard creation...")

    dashboard = MonitoringDashboard()
    assert dashboard is not None, "Dashboard should be created"
    assert dashboard.metrics_collector is not None, "Dashboard should have metrics collector"

    # Test that panels can be created
    overview_panel = dashboard.create_system_overview_panel()
    assert overview_panel is not None, "Overview panel should be created"

    model_panel = dashboard.create_model_usage_panel()
    assert model_panel is not None, "Model panel should be created"

    perf_panel = dashboard.create_performance_panel()
    assert perf_panel is not None, "Performance panel should be created"

    print("  Monitoring dashboard creation tests PASSED")


def main():
    """Run all tests."""
    print("=" * 50)
    print("Testing Monitoring Components")
    print("=" * 50)

    try:
        test_metrics_collector()
        test_convenience_functions()
        test_monitoring_dashboard_creation()

        print("=" * 50)
        print("All monitoring tests PASSED")
        print("=" * 50)
        return 0

    except Exception as e:
        print(f"Testing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())