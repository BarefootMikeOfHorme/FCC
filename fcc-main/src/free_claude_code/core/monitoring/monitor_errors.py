"""
monitor_errors.py

Unified error types for monitoring subsystem.
"""


class MonitoringError(Exception):
    """Base class for monitoring-related errors."""


class MetricsCollectionError(MonitoringError):
    """Raised when a metrics collector fails."""


class ProviderRegistrationError(MonitoringError):
    """Raised when a provider cannot be registered."""


class ConfigurationError(MonitoringError):
    """Raised when monitor configuration is invalid."""
