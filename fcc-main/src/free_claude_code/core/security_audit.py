"""Enhanced security auditing and monitoring for Free Claude Code.

This module provides security-focused auditing capabilities including:
- Immutable audit logs with cryptographic chaining
- Comprehensive security event tracking
- Integration with existing logging infrastructure
- Security metrics and alerting
- Tamper-evident audit trails
"""

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union
from uuid import uuid4

from loguru import logger

# Security audit log directory
AUDIT_DIR = Path.home() / ".fcc" / "audit"
AUDIT_LOG_FILE = AUDIT_DIR / "security_audit.log"
AUDIT_KEY_FILE = AUDIT_DIR / "audit.key"

# Ensure audit directory exists with restrictive permissions
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
if os.name != 'nt':  # Unix-like systems
    os.chmod(AUDIT_DIR, 0o700)

# Audit event types
AUDIT_EVENT_TYPES = {
    "authentication": "User authentication events",
    "authorization": "Authorization and access control events",
    "configuration": "System configuration changes",
    "data_access": "Sensitive data access events",
    "administrative": "Administrative operations",
    "security": "Security-related events (threats, violations)",
    "system": "System operations and health",
    "compliance": "Compliance and regulatory events",
}

# Security levels for events
SECURITY_LEVELS = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _ensure_audit_key() -> bytes:
    """Ensure the audit signing key exists and return it."""
    if not AUDIT_KEY_FILE.exists():
        # Generate a new key for signing audit entries
        key = os.urandom(32)  # 256-bit key
        AUDIT_KEY_FILE.write_bytes(key)
        if os.name != 'nt':
            os.chmod(AUDIT_KEY_FILE, 0o600)
    else:
        key = AUDIT_KEY_FILE.read_bytes()
        if os.name != 'nt':
            os.chmod(AUDIT_KEY_FILE, 0o600)
    return key


def log_security_event(
    event_type: str,
    event_description: str,
    security_level: str = "info",
    user_id: Optional[str] = None,
    source_ip: Optional[str] = None,
    resource_accessed: Optional[str] = None,
    action_taken: Optional[str] = None,
    outcome: str = "success",
    additional_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a security event to the immutable audit trail.

    Args:
        event_type: Type of security event (from AUDIT_EVENT_TYPES)
        event_description: Human-readable description of the event
        security_level: Severity level (info, low, medium, high, critical)
        user_id: Identifier of the user involved (if applicable)
        source_ip: IP address of the source (if applicable)
        resource_accessed: Resource that was accessed (if applicable)
        action_taken: Action that was performed (if applicable)
        outcome: Result of the action (success, failure, blocked, etc.)
        additional_data: Additional structured data for the event
    """
    # Validate inputs
    if event_type not in AUDIT_EVENT_TYPES:
        logger.warning(f"Unknown audit event type: {event_type}. Using 'security'.")
        event_type = "security"

    if security_level not in SECURITY_LEVELS:
        logger.warning(f"Unknown security level: {security_level}. Using 'info'.")
        security_level = "info"

    # Create audit entry
    timestamp = datetime.now(timezone.utc).isoformat()
    entry_id = str(uuid4())

    entry_data = {
        "entry_id": entry_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "event_description": event_description,
        "security_level": security_level,
        "user_id": user_id,
        "source_ip": source_ip,
        "resource_accessed": resource_accessed,
        "action_taken": action_taken,
        "outcome": outcome,
        "additional_data": additional_data or {},
    }

    # Get previous signature for chaining
    previous_signature = _get_last_audit_signature()

    # Sign the entry
    signature = _sign_audit_entry(entry_data, previous_signature)
    entry_data["signature"] = signature.hex()  # Store as hex for JSON

    # Write to audit log
    try:
        # Write the entry as JSON line
        with open(AUDIT_LOG_FILE, 'a') as f:
            f.write(json.dumps(entry_data, separators=(',', ':')) + '\n')

        if os.name != 'nt':
            os.chmod(AUDIT_LOG_FILE, 0o640)  # Readable by owner and group

        # Also log to regular logger for immediate visibility
        logger.bind(
            audit_entry_id=entry_id,
            audit_event_type=event_type,
            audit_security_level=security_level,
            audit_user_id=user_id,
        ).info(f"SECURITY AUDIT: {event_description}")

    except Exception as e:
        logger.error(f"Failed to write security audit entry: {e}")


def _get_last_audit_signature() -> bytes:
    """Get the signature of the last audit entry for chaining."""
    if not AUDIT_LOG_FILE.exists():
        # Genesis block - use all zeros for first signature
        return b'\x00' * 32

    # Read the last entry to get its signature
    try:
        with open(AUDIT_LOG_FILE, 'r') as f:
            lines = f.readlines()

        # Find the last non-empty line
        for line in reversed(lines):
            if line.strip():
                entry = json.loads(line.strip())
                signature_hex = entry.get('signature')
                if signature_hex:
                    return bytes.fromhex(signature_hex)

        # If no signature found, return genesis
        return b'\x00' * 32
    except Exception:
        # If any error, return genesis
        return b'\x00' * 32


def _sign_audit_entry(entry_data: Dict[str, Any], previous_signature: bytes) -> bytes:
    """Create a cryptographic signature for an audit entry."""
    # Serialize entry data deterministically
    serialized = json.dumps(entry_data, sort_keys=True, separators=(',', ':')).encode('utf-8')

    # Chain with previous signature
    chained_data = previous_signature + serialized

    # Create HMAC-SHA256 signature
    key = _ensure_audit_key()
    signature = hmac.new(key, chained_data, hashlib.sha256).digest()

    return signature


def log_authentication_event(
    user_id: str,
    success: bool,
    authentication_method: str,
    source_ip: Optional[str] = None,
    failure_reason: Optional[str] = None,
) -> None:
    """Log an authentication event.

    Args:
        user_id: User attempting to authenticate
        success: Whether authentication succeeded
        authentication_method: Method used (password, api_key, token, etc.)
        source_ip: Source IP address
        failure_reason: Reason for failure (if applicable)
    """
    outcome = "success" if success else "failure"
    security_level = "low" if success else "medium"

    description = f"Authentication {'succeeded' if success else 'failed'} for user '{user_id}' using {authentication_method}"
    if failure_reason:
        description += f": {failure_reason}"

    log_security_event(
        event_type="authentication",
        event_description=description,
        security_level=security_level,
        user_id=user_id,
        source_ip=source_ip,
        action_taken=f"authenticate_via_{authentication_method}",
        outcome=outcome,
        additional_data={
            "authentication_method": authentication_method,
            "failure_reason": failure_reason,
        }
    )


def log_authorization_event(
    user_id: str,
    resource: str,
    action: str,
    granted: bool,
    policy_rule: Optional[str] = None,
) -> None:
    """Log an authorization (access control) event.

    Args:
        user_id: User attempting the action
        resource: Resource being accessed
        action: Action being performed (read, write, execute, etc.)
        granted: Whether access was granted
        policy_rule: Specific policy rule that was evaluated
    """
    outcome = "granted" if granted else "denied"
    security_level = "low" if granted else "medium"

    description = f"Access {outcome} for user '{user_id}' to {resource} for action '{action}'"

    log_security_event(
        event_type="authorization",
        event_description=description,
        security_level=security_level,
        user_id=user_id,
        resource_accessed=resource,
        action_taken=f"authorize_{action}",
        outcome=outcome,
        additional_data={
            "resource": resource,
            "action": action,
            "granted": granted,
            "policy_rule": policy_rule,
        }
    )


def log_configuration_change(
    user_id: Optional[str],
    config_key: str,
    old_value: Any,
    new_value: Any,
    config_source: str = "unknown",
) -> None:
    """Log a configuration change event.

    Args:
        user_id: User making the change (if applicable)
        config_key: Configuration key that was changed
        old_value: Previous value
        new_value: New value
        config_source: Source of configuration (environment, file, etc.)
    """
    # Redact sensitive values for audit log
    def _redact_value(val: Any) -> Any:
        if isinstance(val, str) and any(secret in val.lower() for secret in
                                      ['key', 'token', 'secret', 'password']):
            return "<redacted>"
        return val

    description = f"Configuration changed: {config_key} = {_redact_value(new_value)}"

    log_security_event(
        event_type="configuration",
        event_description=description,
        security_level="medium",
        user_id=user_id,
        action_taken="modify_configuration",
        outcome="success",
        additional_data={
            "config_key": config_key,
            "old_value": _redact_value(old_value),
            "new_value": _redact_value(new_value),
            "config_source": config_source,
        }
    )


def log_data_access_event(
    user_id: str,
    resource_type: str,
    resource_identifier: str,
    operation: str,
    sensitivity_level: str = "internal",
) -> None:
    """Log access to sensitive data.

    Args:
        user_id: User accessing the data
        resource_type: Type of resource (memory, file, key, etc.)
        resource_identifier: Specific resource being accessed
        operation: Operation performed (read, write, delete, etc.)
        sensitivity_level: Sensitivity of the data (public, internal, confidential, restricted)
    """
    security_level_map = {
        "public": "info",
        "internal": "low",
        "confidential": "medium",
        "restricted": "high",
    }
    security_level = security_level_map.get(sensitivity_level, "low")

    description = f"{operation.upper()} {resource_type} '{resource_identifier}' by user '{user_id}'"

    log_security_event(
        event_type="data_access",
        event_description=description,
        security_level=security_level,
        user_id=user_id,
        resource_accessed=f"{resource_type}:{resource_identifier}",
        action_taken=f"{operation}_{resource_type}",
        outcome="success",
        additional_data={
            "resource_type": resource_type,
            "resource_identifier": resource_identifier,
            "operation": operation,
            "sensitivity_level": sensitivity_level,
        }
    )


def log_security_violation(
    violation_type: str,
    description: str,
    user_id: Optional[str] = None,
    source_ip: Optional[str] = None,
    blocked: bool = True,
) -> None:
    """Log a security violation or threat event.

    Args:
        violation_type: Type of violation (intrusion_attempt, malware_detected, etc.)
        description: Detailed description of the violation
        user_id: User associated with the violation (if applicable)
        source_ip: Source IP address (if applicable)
        blocked: Whether the violation was blocked/prevented
    """
    outcome = "blocked" if blocked else "detected"
    security_level = "high"

    log_security_event(
        event_type="security",
        event_description=f"Security violation: {description}",
        security_level=security_level,
        user_id=user_id,
        source_ip=source_ip,
        action_taken=f"respond_to_{violation_type}",
        outcome=outcome,
        additional_data={
            "violation_type": violation_type,
            "blocked": blocked,
        }
    )


def log_administrative_action(
    user_id: str,
    action: str,
    target: Optional[str] = None,
    outcome: str = "success",
) -> None:
    """Log an administrative action.

    Args:
        user_id: User performing the action
        action: Administrative action performed
        target: Target of the action (if applicable)
        outcome: Result of the action
    """
    description = f"Administrative action: {action} by user '{user_id}'"
    if target:
        description += f" on {target}"

    log_security_event(
        event_type="administrative",
        event_description=description,
        security_level="low",
        user_id=user_id,
        action_taken=action,
        outcome=outcome,
        additional_data={
            "target": target,
        }
    )


def log_system_event(
    event_description: str,
    component: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a system operation or health event.

    Args:
        event_description: Description of the system event
        component: System component involved (if applicable)
        metrics: Performance or health metrics (if applicable)
    """
    log_security_event(
        event_type="system",
        event_description=event_description,
        security_level="info",
        action_taken="system_operation",
        outcome="success",
        additional_data={
            "component": component,
            "metrics": metrics or {},
        }
    )


def log_compliance_event(
    regulation: str,
    requirement: str,
    compliance_status: str,
    evidence_reference: Optional[str] = None,
) -> None:
    """Log a compliance-related event.

    Args:
        regulation: Regulation or standard (GDPR, HIPAA, etc.)
        requirement: Specific requirement being addressed
        compliance_status: Status (compliant, non_compliant, partially_compliant)
        evidence_reference: Reference to evidence supporting the status
    """
    security_level = "medium" if compliance_status != "compliant" else "low"

    description = f"Compliance check: {regulation} {requirement} - {compliance_status}"

    log_security_event(
        event_type="compliance",
        event_description=description,
        security_level=security_level,
        action_taken="compliance_check",
        outcome=compliance_status,
        additional_data={
            "regulation": regulation,
            "requirement": requirement,
            "compliance_status": compliance_status,
            "evidence_reference": evidence_reference,
        }
    )


def verify_audit_integrity() -> bool:
    """Verify the integrity of the security audit trail.

    Returns:
        bool: True if audit chain is valid, False otherwise
    """
    if not AUDIT_LOG_FILE.exists():
        return True  # No chain to verify

    try:
        key = _ensure_audit_key()
        previous_signature = b'\x00' * 32  # Genesis

        with open(AUDIT_LOG_FILE, 'r') as f:
            lines = f.readlines()

        # Verify each entry
        for i, line in enumerate(lines):
            if not line.strip():
                continue

            entry = json.loads(line.strip())
            # Remove signature field for verification and convert from hex
            signature_hex = entry.pop('signature', None)
            if signature_hex is None:
                logger.error(f"Missing signature for audit entry {i}")
                return False
            signature_bytes = bytes.fromhex(signature_hex)

            # Calculate expected signature
            expected_signature = _sign_audit_entry(entry, previous_signature)

            # Compare with extracted signature
            if not hmac.compare_digest(expected_signature, signature_bytes):
                logger.error(f"Audit chain verification failed at entry {i}")
                return False

            # Update for next iteration
            previous_signature = expected_signature

        return True
    except Exception as e:
        logger.error(f"Error verifying audit chain: {e}")
        return False


def get_audit_stats() -> Dict[str, Any]:
    """Get statistics about the audit log.

    Returns:
        Dict containing audit log statistics
    """
    stats = {
        "total_entries": 0,
        "by_event_type": {},
        "by_security_level": {},
        "latest_entry": None,
        "chain_valid": False,
        "log_size_bytes": 0,
    }

    if not AUDIT_LOG_FILE.exists():
        return stats

    try:
        stats["log_size_bytes"] = AUDIT_LOG_FILE.stat().st_size

        event_counts = {}
        level_counts = {}
        latest_timestamp = None
        latest_entry = None

        with open(AUDIT_LOG_FILE, 'r') as f:
            for line_num, line in enumerate(f):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line.strip())
                    stats["total_entries"] += 1

                    # Count by event type
                    event_type = entry.get("event_type", "unknown")
                    event_counts[event_type] = event_counts.get(event_type, 0) + 1

                    # Count by security level
                    security_level = entry.get("security_level", "unknown")
                    level_counts[security_level] = level_counts.get(security_level, 0) + 1

                    # Track latest entry
                    timestamp = entry.get("timestamp")
                    if timestamp:
                        if latest_timestamp is None or timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                            latest_entry = {
                                "entry_id": entry.get("entry_id"),
                                "timestamp": timestamp,
                                "event_type": event_type,
                                "description": entry.get("event_description", ""),
                                "security_level": security_level,
                            }
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in audit log at line {line_num + 1}")

        stats["by_event_type"] = event_counts
        stats["by_security_level"] = level_counts
        stats["latest_entry"] = latest_entry
        stats["chain_valid"] = verify_audit_integrity()

    except Exception as e:
        logger.error(f"Error getting audit stats: {e}")

    return stats


# Convenience functions for common security events
def log_api_key_access(provider: str, user_id: str, action: str = "access") -> None:
    """Log access to an API key."""
    log_data_access_event(
        user_id=user_id,
        resource_type="api_key",
        resource_identifier=provider,
        operation=action,
        sensitivity_level="restricted",
    )


def log_memory_access(user_id: str, memory_id: str, operation: str = "read") -> None:
    """Log access to persistent memory."""
    log_data_access_event(
        user_id=user_id,
        resource_type="memory",
        resource_identifier=memory_id,
        operation=operation,
        sensitivity_level="confidential",
    )


def log_configuration_access(user_id: str, config_key: str) -> None:
    """Log access to configuration."""
    log_data_access_event(
        user_id=user_id,
        resource_type="configuration",
        resource_identifier=config_key,
        operation="read",
        sensitivity_level="confidential",
    )


def log_threat_detected(threat_type: str, description: str, blocked: bool = True) -> None:
    """Log detection of a security threat."""
    log_security_violation(
        violation_type=threat_type,
        description=description,
        blocked=blocked,
    )


# Initialize audit system on module import
def _initialize_audit_system():
    """Initialize the audit system components."""
    # Ensure audit directory exists with proper permissions
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        os.chmod(AUDIT_DIR, 0o700)

    # Log audit system initialization
    log_system_event(
        event_description="Security audit system initialized",
        component="security_audit",
        metrics={
            "audit_dir": str(AUDIT_DIR),
            "audit_log_file": str(AUDIT_LOG_FILE),
        }
    )


# Run initialization when module is imported
_initialize_audit_system()