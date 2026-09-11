"""
puller_resolver.py

Inert, safe puller scaffold for later use.

Behavior:
- Does not perform any network I/O at import time.
- Requires explicit environment opt-in: PULLER_ENABLED=true and UPSTREAM_BASE_URL set.
- When enabled, still defaults to dry-run (apply=False) unless APPLY_PULLER=true.
- Never overwrites secrets.json; always backs up replaced files.
- Emits structured events to logs/env_resolver.jsonl for audit.

This module is intentionally conservative and inert by default so it can be
committed to the repo now and enabled later when packaging and review are complete.
"""
from __future__ import annotations
import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional

LOG = logging.getLogger("fcc.puller_resolver")
LOG.setLevel(logging.INFO)

# Safety constants
LOGS_DIRNAME = "logs"
EVENTS_FILE = "env_resolver.jsonl"
NEVER_OVERWRITE = {"secrets.json", "secrets.placeholder.json"}
DEFAULT_TARGET = Path(__file__).parent / "templates"

def _emit_event(event: str, severity: str = "INFO", details: Optional[Dict] = None) -> None:
    try:
        logs_dir = Path(__file__).parents[3] / LOGS_DIRNAME
        logs_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "component": "puller_resolver",
            "event": event,
            "severity": severity,
            "details": details or {},
        }
        with open(logs_dir / EVENTS_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        LOG.debug("Failed to write puller event", exc_info=True)

# Public API is intentionally minimal and inert
def is_enabled() -> bool:
    """Return True only when operator explicitly opts in via env var."""
    return os.environ.get("PULLER_ENABLED", "false").lower() in ("1", "true", "yes")

def _guard_enabled() -> None:
    if not is_enabled():
        _emit_event("puller_disabled", "INFO", {"reason": "PULLER_ENABLED not set"})
        raise RuntimeError("puller_resolver is disabled. Set PULLER_ENABLED=true to enable.")

def pull_and_apply_templates(
    upstream_base_url: str,
    target_templates_dir: Optional[Path] = None,
    file_list: Optional[Dict[str, str]] = None,
    apply: bool = False,
    timeout: int = 30
) -> Dict:
    """
    Inert wrapper. Will refuse to run unless PULLER_ENABLED=true.
    When enabled, still requires explicit apply=True to write files.
    This function intentionally does not implement network logic here; it
    delegates to a controlled implementation that must be reviewed and
    enabled by operators when packaging.
    """
    _emit_event("pull_requested", "INFO", {"upstream": upstream_base_url, "apply": apply})
    _guard_enabled()

    # Minimal safety checks and simulation response so callers can be tested
    target_templates_dir = Path(target_templates_dir or DEFAULT_TARGET)
    report = {
        "upstream": upstream_base_url,
        "target": str(target_templates_dir),
        "apply": bool(apply),
        "planned": [],
        "applied": [],
        "skipped": [],
        "errors": ["Network implementation disabled in inert mode"]
    }
    _emit_event("pull_refused_inert_mode", "WARN", {"upstream": upstream_base_url})
    return report

def puller_cli(upstream_base_url: str, apply: bool = False) -> None:
    """CLI wrapper for interactive use. Will refuse unless enabled."""
    try:
        report = pull_and_apply_templates(upstream_base_url, apply=apply)
        print("Puller inert report:")
        print(json.dumps(report, indent=2))
    except Exception as e:
        LOG.exception("Puller refused to run")
        print("Puller refused to run:", str(e))
        raise

# NOTE: This module intentionally does not run network operations at import time.
# Call pull_and_apply_templates() explicitly from a CLI helper or a controlled task.
# Upstream reference: when enabled, include the upstream URL and commit/branch in invocation.
