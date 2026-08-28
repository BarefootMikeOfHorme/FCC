#!/usr/bin/env python3
"""Debug script for the security audit system."""

import sys
import os
import json
import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Add the src directory to the path so we can import free_claude_code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from free_claude_code.core.security_audit import (
    _ensure_audit_key,
    _get_last_audit_signature,
    _sign_audit_entry,
    AUDIT_LOG_FILE,
    AUDIT_KEY_FILE
)

def debug_audit_chain():
    """Debug the audit chain verification."""
    print("Debugging audit chain...")

    # Ensure we start fresh
    if AUDIT_LOG_FILE.exists():
        AUDIT_LOG_FILE.unlink()
    if AUDIT_KEY_FILE.exists():
        AUDIT_KEY_FILE.unlink()

    # Clear the audit directory
    AUDIT_DIR = Path.home() / ".fcc" / "audit"
    if AUDIT_DIR.exists():
        import shutil
        shutil.rmtree(AUDIT_DIR)

    # Make sure directory exists
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize
    key = _ensure_audit_key()
    print(f"Audit key: {key.hex()}")

    # Create a simple entry
    timestamp = datetime.now(timezone.utc).isoformat()
    entry_id = str(uuid4())

    entry_data = {
        "entry_id": entry_id,
        "timestamp": timestamp,
        "event_type": "test",
        "event_description": "Test event",
        "security_level": "info",
        "user_id": "test_user",
        "source_ip": "127.0.0.1",
        "action_taken": "test_action",
        "outcome": "success",
        "additional_data": {"test": "data"}
    }

    print(f"Entry data (first): {json.dumps(entry_data, sort_keys=True)}")

    # Get previous signature for chaining
    previous_signature = _get_last_audit_signature()
    print(f"Previous signature (first): {previous_signature.hex()}")

    # Sign the entry
    signature = _sign_audit_entry(entry_data, previous_signature)
    print(f"Signature (first): {signature.hex()}")

    # Add signature to entry data
    entry_data_with_sig = entry_data.copy()
    entry_data_with_sig["signature"] = signature.hex()

    # Write to audit log
    with open(AUDIT_LOG_FILE, 'a') as f:
        f.write(json.dumps(entry_data_with_sig, separators=(',', ':')) + '\n')

    print("First entry written.")

    # Create second entry
    timestamp2 = datetime.now(timezone.utc).isoformat()
    entry_id2 = str(uuid4())

    entry_data2 = {
        "entry_id": entry_id2,
        "timestamp": timestamp2,
        "event_type": "test",
        "event_description": "Test event 2",
        "security_level": "info",
        "user_id": "test_user",
        "source_ip": "127.0.0.1",
        "action_taken": "test_action",
        "outcome": "success",
        "additional_data": {"test": "data2"}
    }

    print(f"Entry data (second): {json.dumps(entry_data2, sort_keys=True)}")

    # Get previous signature for chaining
    previous_signature2 = _get_last_audit_signature()
    print(f"Previous signature (second): {previous_signature2.hex()}")
    print(f"Expected previous signature: {signature.hex()}")

    # Sign the entry
    signature2 = _sign_audit_entry(entry_data2, previous_signature2)
    print(f"Signature (second): {signature2.hex()}")

    # Add signature to entry data
    entry_data2_with_sig = entry_data2.copy()
    entry_data2_with_sig["signature"] = signature2.hex()

    # Write to audit log
    with open(AUDIT_LOG_FILE, 'a') as f:
        f.write(json.dumps(entry_data2_with_sig, separators=(',', ':')) + '\n')

    print("Second entry written.")

    # Now let's verify manually
    print("\n--- Manual Verification ---")

    with open(AUDIT_LOG_FILE, 'r') as f:
        lines = f.readlines()

    print(f"Number of lines: {len(lines)}")

    # Verify first entry
    line1 = lines[0].strip()
    entry1 = json.loads(line1)
    print(f"First entry: {entry1}")

    signature_hex1 = entry1.pop('signature')
    print(f"First entry signature hex: {signature_hex1}")
    signature_bytes1 = bytes.fromhex(signature_hex1)
    print(f"First entry signature bytes: {signature_bytes1.hex()}")

    # Calculate expected signature for first entry
    expected_sig1 = _sign_audit_entry(entry1, b'\x00' * 32)
    print(f"Expected signature (first): {expected_sig1.hex()}")
    print(f"Match first: {hmac.compare_digest(expected_sig1, signature_bytes1)}")

    # Verify second entry
    line2 = lines[1].strip()
    entry2 = json.loads(line2)
    print(f"Second entry: {entry2}")

    signature_hex2 = entry2.pop('signature')
    print(f"Second entry signature hex: {signature_hex2}")
    signature_bytes2 = bytes.fromhex(signature_hex2)
    print(f"Second entry signature bytes: {signature_bytes2.hex()}")

    # Calculate expected signature for second entry
    expected_sig2 = _sign_audit_entry(entry2, expected_sig1)
    print(f"Expected signature (second): {expected_sig2.hex()}")
    print(f"Match second: {hmac.compare_digest(expected_sig2, signature_bytes2)}")

if __name__ == "__main__":
    debug_audit_chain()