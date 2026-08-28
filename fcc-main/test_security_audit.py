#!/usr/bin/env python3
"""Test script for the security audit system."""

import sys
import os

# Add the src directory to the path so we can import free_claude_code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_security_audit():
    """Test the security audit system."""
    try:
        from free_claude_code.core.security_audit import (
            log_security_event,
            log_authentication_event,
            log_authorization_event,
            log_configuration_change,
            log_data_access_event,
            log_security_violation,
            log_administrative_action,
            log_system_event,
            log_compliance_event,
            verify_audit_integrity,
            get_audit_stats,
            log_api_key_access,
            log_memory_access,
            log_threat_detected,
        )

        print("Testing security audit system...")

        # Test basic security event logging
        log_security_event(
            event_type="security",
            event_description="Test security event",
            security_level="medium",
            user_id="test_user",
            source_ip="127.0.0.1",
            action_taken="test_action",
            outcome="success",
            additional_data={"test": "data"}
        )
        print("+ Basic security event logged")

        # Test authentication event
        log_authentication_event(
            user_id="test_user",
            success=True,
            authentication_method="api_key",
            source_ip="127.0.0.1"
        )
        print("+ Authentication event logged")

        # Test authorization event
        log_authorization_event(
            user_id="test_user",
            resource="test_resource",
            action="read",
            granted=True,
            policy_rule="allow_read"
        )
        print("+ Authorization event logged")

        # Test configuration change
        log_configuration_change(
            user_id="test_user",
            config_key="test.setting",
            old_value="old_value",
            new_value="new_value",
            config_source="test"
        )
        print("+ Configuration change logged")

        # Test data access
        log_data_access_event(
            user_id="test_user",
            resource_type="file",
            resource_identifier="/test/path",
            operation="read",
            sensitivity_level="confidential"
        )
        print("+ Data access event logged")

        # Test security violation
        log_security_violation(
            violation_type="intrusion_attempt",
            description="Test intrusion attempt detected",
            source_ip="192.168.1.100",
            blocked=True
        )
        print("+ Security violation logged")

        # Test administrative action
        log_administrative_action(
            user_id="admin_user",
            action="system_restart",
            target="free_claude_code_service",
            outcome="success"
        )
        print("+ Administrative action logged")

        # Test system event
        log_system_event(
            event_description="System health check passed",
            component="health_monitor",
            metrics={"cpu_usage": 45.2, "memory_usage": 62.8}
        )
        print("+ System event logged")

        # Test compliance event
        log_compliance_event(
            regulation="GDPR",
            requirement="Data subject access request",
            compliance_status="compliant",
            evidence_reference="DSAR-2026-0824-001"
        )
        print("+ Compliance event logged")

        # Test convenience functions
        log_api_key_access("openai", "test_user", "read")
        print("+ API key access logged")

        log_memory_access("test_user", "mem_123456", "write")
        print("+ Memory access logged")

        log_threat_detected("malware", "Test malware detected in file", blocked=True)
        print("+ Threat detection logged")

        # Verify audit integrity
        is_valid = verify_audit_integrity()
        print(f"+ Audit chain validation: {'PASS' if is_valid else 'FAIL'}")

        # Get audit statistics
        stats = get_audit_stats()
        print(f"+ Audit statistics: {stats['total_entries']} entries")
        print(f"  Event types: {list(stats['by_event_type'].keys())}")
        print(f"  Security levels: {list(stats['by_security_level'].keys())}")

        print("\nAll tests completed successfully!")
        return True

    except Exception as e:
        print(f"x Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_security_audit()
    sys.exit(0 if success else 1)