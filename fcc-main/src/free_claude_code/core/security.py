"""Security utilities for Free Claude Code including encryption for API keys.

This module provides:
- Master-key based symmetric encryption for API keys
- Per-provider encrypted key files under ~/.fcc/keys
- Restrictive filesystem permissions (Unix)
- Safe-to-fail loading and deletion semantics

It is intentionally simple and provider-neutral, and does not attempt to be a
general-purpose secret manager.
"""

import os
import base64
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

# Optional FCC integrations
try:
    from .logging_integration import log_with_context
except Exception:
    def log_with_context(message: str, level: str = "info", **ctx: object) -> None:
        return

try:
    from .trace import trace_event
except Exception:
    def trace_event(event: str, **fields: object) -> None:
        return


# Directory for storing encryption keys and encrypted secrets
FCC_DIR = Path.home() / ".fcc"
KEYS_DIR = FCC_DIR / "keys"
MASTER_KEY_FILE = KEYS_DIR / "master.key"


def ensure_keys_directory() -> None:
    """Ensure the keys directory exists with restrictive permissions."""
    trace_event("security.ensure_keys_directory", path=str(KEYS_DIR))

    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(KEYS_DIR, 0o700)
        except Exception:
            log_with_context(
                "Failed to chmod keys directory.",
                level="warning",
                path=str(KEYS_DIR),
            )


def generate_or_load_master_key() -> bytes:
    """Generate or load the master encryption key."""
    trace_event("security.generate_or_load_master_key", path=str(MASTER_KEY_FILE))

    ensure_keys_directory()

    if MASTER_KEY_FILE.exists():
        try:
            with open(MASTER_KEY_FILE, "rb") as f:
                key = f.read()
        except Exception as e:
            log_with_context(
                "Failed to read master key file.",
                level="error",
                path=str(MASTER_KEY_FILE),
                error=str(e),
            )
            raise

        if os.name != "nt":
            try:
                os.chmod(MASTER_KEY_FILE, 0o600)
            except Exception:
                log_with_context(
                    "Failed to chmod master key file.",
                    level="warning",
                    path=str(MASTER_KEY_FILE),
                )
        return key

    key = Fernet.generate_key()
    try:
        with open(MASTER_KEY_FILE, "wb") as f:
            f.write(key)
    except Exception as e:
        log_with_context(
            "Failed to write master key file.",
            level="error",
            path=str(MASTER_KEY_FILE),
            error=str(e),
        )
        raise

    if os.name != "nt":
        try:
            os.chmod(MASTER_KEY_FILE, 0o600)
        except Exception:
            log_with_context(
                "Failed to chmod master key file after creation.",
                level="warning",
                path=str(MASTER_KEY_FILE),
            )

    return key


def get_cipher() -> Fernet:
    """Get a Fernet cipher instance for encryption/decryption."""
    trace_event("security.get_cipher")
    key = generate_or_load_master_key()
    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for secure storage."""
    trace_event("security.encrypt_api_key")

    if not api_key:
        return ""

    cipher = get_cipher()
    encrypted_bytes = cipher.encrypt(api_key.encode("utf-8"))
    return base64.urlsafe_b64encode(encrypted_bytes).decode("utf-8")


def decrypt_api_key(encrypted_api_key: str) -> str:
    """Decrypt an API key from secure storage."""
    trace_event("security.decrypt_api_key")

    if not encrypted_api_key:
        return ""

    try:
        cipher = get_cipher()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_api_key.encode("utf-8"))
        decrypted_bytes = cipher.decrypt(encrypted_bytes)
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        log_with_context(
            "Failed to decrypt API key.",
            level="error",
            error=str(e),
        )
        raise ValueError(f"Failed to decrypt API key: {e}")


def store_api_key(provider: str, api_key: str) -> Path:
    """Store an encrypted API key for a provider."""
    trace_event("security.store_api_key", provider=provider)

    ensure_keys_directory()
    key_file = KEYS_DIR / f"{provider}.key"

    encrypted_key = encrypt_api_key(api_key)

    try:
        with open(key_file, "w") as f:
            f.write(encrypted_key)
    except Exception as e:
        log_with_context(
            "Failed to write provider key file.",
            level="error",
            provider=provider,
            path=str(key_file),
            error=str(e),
        )
        raise

    if os.name != "nt":
        try:
            os.chmod(key_file, 0o600)
        except Exception:
            log_with_context(
                "Failed to chmod provider key file.",
                level="warning",
                provider=provider,
                path=str(key_file),
            )

    return key_file


def load_api_key(provider: str) -> Optional[str]:
    """Load an API key for a provider from secure storage."""
    trace_event("security.load_api_key", provider=provider)

    ensure_keys_directory()
    key_file = KEYS_DIR / f"{provider}.key"

    if not key_file.exists():
        return None

    try:
        with open(key_file, "r") as f:
            encrypted_key = f.read().strip()
    except Exception as e:
        log_with_context(
            "Failed to read provider key file.",
            level="error",
            provider=provider,
            path=str(key_file),
            error=str(e),
        )
        return None

    if not encrypted_key:
        return None

    try:
        return decrypt_api_key(encrypted_key)
    except Exception:
        return None


def delete_api_key(provider: str) -> bool:
    """Delete an API key for a provider from secure storage."""
    trace_event("security.delete_api_key", provider=provider)

    ensure_keys_directory()
    key_file = KEYS_DIR / f"{provider}.key"

    if key_file.exists():
        try:
            key_file.unlink()
            return True
        except Exception as e:
            log_with_context(
                "Failed to delete provider key file.",
                level="error",
                provider=provider,
                path=str(key_file),
                error=str(e),
            )
            return False
    return False
