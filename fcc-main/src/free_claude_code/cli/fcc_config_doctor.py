#!/usr/bin/env python3
"""fcc-config doctor: inspect and optionally repair FCC config resolution."""
import argparse
import logging
from pathlib import Path
import os

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger("fcc.config_doctor")

try:
    from free_claude_code.config import env_resolver
except Exception:
    env_resolver = None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repair", action="store_true", help="Attempt self-heal if issues found")
    args = p.parse_args()

    if env_resolver is None:
        LOG.error("env_resolver not importable. Ensure package is installed or run from repo root.")
        return 2

    cfg = env_resolver.resolve()
    LOG.info("Resolved FCC_CONFIG_DIR=%s", cfg)
    missing = []
    for f in ["config.yaml", "providers.json", "secrets.json", "admin.json"]:
        if not (cfg / f).exists():
            missing.append(f)
    if missing:
        LOG.warning("Missing files: %s", missing)
        if args.repair:
            LOG.info("Repair requested: creating placeholders for missing files")
            for f in missing:
                fp = cfg / f
                if f.endswith(".json"):
                    fp.write_text("{}")
                else:
                    fp.write_text("# default")
            LOG.info("Repair complete")
        else:
            LOG.info("Run with --repair to create placeholders")
    else:
        LOG.info("All required files present")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
