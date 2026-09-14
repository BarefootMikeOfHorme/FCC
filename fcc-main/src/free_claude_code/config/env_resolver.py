"""
env_resolver.py

Discover FCC config dir, validate, self-heal, and expose FCC_CONFIG_DIR.
Properties:
- Discovery order: FCC_CONFIG_DIR env -> WSL Windows user config -> platform user config -> repo fallback -> create defaults
- Validation: existence, parseable JSON/YAML, minimal schema checks
- Self-heal: restore from backup/, restore from templates/, generate placeholders for secrets (never generate real secrets)
- Backups: move corrupt files to backup/<name>.corrupt.<ts>.bak before repair
- Migrations: versioned, idempotent migration stubs with migrations.log
- Observability: structured JSON events to logs/env_resolver.jsonl and human console logs
"""
from __future__ import annotations
import os
import json
import logging
import shutil
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    import yaml
except Exception:
    yaml = None  # optional; YAML validation only if PyYAML is installed

LOG = logging.getLogger("fcc.env_resolver")
LOG.setLevel(logging.INFO)

# File names required in a config dir
DEFAULT_FILES = ["config.yaml", "providers.json", "secrets.json", "admin.json"]

# Templates directory (relative to this file)
TEMPLATES_DIR = Path(__file__).parent / "templates"
HEALTH_DIRNAME = "health"
LOGS_DIRNAME = "logs"
ENV_LOG_FILE = LOGS_DIRNAME + "/env_resolver.jsonl"
LOCK_FILENAME = "config.lock"
HEALTH_FILENAME = "health.json"
MIGRATIONS_LOG = "migrations.log"
BACKUP_DIRNAME = "backup"

# Minimal schema checks (keys expected)
MINIMAL_SCHEMA = {
    "config.yaml": ["version", "server"],
    "providers.json": ["providers"],
    "admin.json": ["admin_setup_required", "admin"],
}

# Utility: write structured JSON event to logs/env_resolver.jsonl
def _emit_event(event: str, severity: str = "INFO", details: Optional[Dict[str, Any]] = None) -> None:
    try:
        logs_dir = Path(__file__).parents[3] / LOGS_DIRNAME
        logs_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "event": event,
            "severity": severity,
            "details": details or {},
        }
        with open(logs_dir / "env_resolver.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        # Best-effort only; do not raise
        LOG.debug("Failed to write structured event", exc_info=True)

def running_in_wsl() -> bool:
    try:
        return "microsoft" in os.uname().release.lower()
    except Exception:
        # Fallback: check environment hint
        return bool(os.environ.get("WSL_DISTRO_NAME"))

def _windows_user_config_path() -> Optional[Path]:
    # When running in WSL, prefer Windows user config under /mnt/c/Users/<User>/.fcc
    try:
        user = os.environ.get("USERNAME") or os.environ.get("USER")
        if not user:
            return None
        candidate = Path("/mnt/c/Users") / user / ".fcc"
        return candidate
    except Exception:
        return None

def _platform_user_config() -> Path:
    # On Windows use %USERPROFILE%\.fcc, on Linux/mac use $HOME/.fcc
    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home())
    return home / ".fcc"

def _repo_fallback_config() -> Path:
    # repo root assumed 3 parents up from this file
    return Path(__file__).parents[3] / ".fcc"

def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def _backup_file(cfg_dir: Path, filename: str) -> Optional[Path]:
    try:
        backup_dir = cfg_dir / BACKUP_DIRNAME
        _ensure_dir(backup_dir)
        ts = int(time.time())
        src = cfg_dir / filename
        if not src.exists():
            return None
        dst = backup_dir / f"{filename}.corrupt.{ts}.bak"
        shutil.move(str(src), str(dst))
        _emit_event("backup_created", "INFO", {"file": filename, "backup": str(dst)})
        return dst
    except Exception as e:
        _emit_event("backup_failed", "WARN", {"file": filename, "error": str(e)})
        return None

def _read_file(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None

def _parse_file(path: Path) -> bool:
    """
    Return True if file parses as JSON or YAML depending on extension.
    """
    try:
        text = _read_file(path)
        if text is None:
            return False
        if path.suffix.lower() in (".json",):
            json.loads(text)
            return True
        if path.suffix.lower() in (".yml", ".yaml"):
            if yaml:
                yaml.safe_load(text)
                return True
            else:
                # If PyYAML not available, do a light check for colon presence
                return ":" in text
        # Unknown extension: accept as present
        return True
    except Exception:
        return False

def _minimal_schema_ok(path: Path) -> bool:
    """
    Check minimal schema keys for known files.
    """
    try:
        if path.name not in MINIMAL_SCHEMA:
            return True
        text = _read_file(path)
        if text is None:
            return False
        if path.suffix.lower() == ".json":
            data = json.loads(text)
        elif yaml and path.suffix.lower() in (".yml", ".yaml"):
            data = yaml.safe_load(text)
        else:
            # best-effort: if keys appear as substrings
            for k in MINIMAL_SCHEMA[path.name]:
                if k not in text:
                    return False
            return True
        for key in MINIMAL_SCHEMA[path.name]:
            if key not in data:
                return False
        return True
    except Exception:
        return False

def _restore_from_template(cfg_dir: Path, filename: str) -> bool:
    try:
        tpl = TEMPLATES_DIR / filename
        if tpl.exists():
            shutil.copy(str(tpl), str(cfg_dir / filename))
            _emit_event("restored_from_template", "INFO", {"file": filename})
            return True
        return False
    except Exception as e:
        _emit_event("restore_failed", "WARN", {"file": filename, "error": str(e)})
        return False

def _generate_placeholder(cfg_dir: Path, filename: str) -> bool:
    try:
        dst = cfg_dir / filename
        if filename.endswith(".json"):
            dst.write_text("{}", encoding="utf-8")
        else:
            dst.write_text("# generated placeholder\n", encoding="utf-8")
        _emit_event("generated_placeholder", "WARN", {"file": filename})
        return True
    except Exception as e:
        _emit_event("generate_failed", "ERROR", {"file": filename, "error": str(e)})
        return False

def _validate_and_self_heal(cfg_dir: Path, auto_repair: bool = False) -> Dict[str, Any]:
    """
    Validate required files. If missing or corrupt, attempt self-heal.
    Returns a health dict describing actions taken.
    """
    health = {"checked_at": time.time(), "path": str(cfg_dir), "repairs": []}
    _ensure_dir(cfg_dir)
    # Ensure health and backup dirs exist
    _ensure_dir(cfg_dir / HEALTH_DIRNAME)
    _ensure_dir(cfg_dir / BACKUP_DIRNAME)

    for fname in DEFAULT_FILES:
        fpath = cfg_dir / fname
        if not fpath.exists():
            _emit_event("missing_file", "WARN", {"file": fname})
            if auto_repair:
                # Try restore from backup first
                backup_dir = cfg_dir / BACKUP_DIRNAME
                restored = False
                if backup_dir.exists():
                    # pick latest backup for this file
                    candidates = sorted(backup_dir.glob(f"{fname}*"), reverse=True)
                    if candidates:
                        shutil.copy(str(candidates[0]), str(fpath))
                        restored = True
                        health["repairs"].append({"file": fname, "action": "restored_from_backup", "source": str(candidates[0])})
                        _emit_event("restored_from_backup", "INFO", {"file": fname, "source": str(candidates[0])})
                if not restored:
                    # restore from template if available
                    if _restore_from_template(cfg_dir, fname):
                        health["repairs"].append({"file": fname, "action": "restored_from_template"})
                    else:
                        # generate placeholder for secrets only if template missing
                        if fname == "secrets.json":
                            # do not auto-generate real secrets; create placeholder
                            _generate_placeholder(cfg_dir, "secrets.placeholder.json")
                            health["repairs"].append({"file": fname, "action": "created_placeholder", "note": "secrets not auto-generated"})
                        else:
                            _generate_placeholder(cfg_dir, fname)
                            health["repairs"].append({"file": fname, "action": "generated_placeholder"})
        else:
            # file exists: validate parse and minimal schema
            ok = _parse_file(fpath)
            schema_ok = _minimal_schema_ok(fpath)
            if not ok or not schema_ok:
                _emit_event("corrupt_file", "WARN", {"file": fname, "parse_ok": ok, "schema_ok": schema_ok})
                # backup corrupt file
                _backup_file(cfg_dir, fname)
                if auto_repair:
                    if _restore_from_template(cfg_dir, fname):
                        health["repairs"].append({"file": fname, "action": "restored_from_template_after_corrupt"})
                    else:
                        _generate_placeholder(cfg_dir, fname)
                        health["repairs"].append({"file": fname, "action": "generated_placeholder_after_corrupt"})
                else:
                    health["repairs"].append({"file": fname, "action": "backed_up_corrupt"})
    # write health.json
    try:
        health_path = cfg_dir / HEALTH_DIRNAME / HEALTH_FILENAME
        health_path.write_text(json.dumps(health, default=str, indent=2), encoding="utf-8")
    except Exception:
        _emit_event("health_write_failed", "WARN", {"path": str(cfg_dir / HEALTH_DIRNAME / HEALTH_FILENAME)})
    return health

def _write_lock(cfg_dir: Path) -> None:
    try:
        lock = {
            "pid": os.getpid(),
            "resolved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "resolved_path": str(cfg_dir),
            "platform": os.name,
            "wsl": running_in_wsl(),
        }
        (cfg_dir / LOCK_FILENAME).write_text(json.dumps(lock), encoding="utf-8")
    except Exception:
        _emit_event("lock_write_failed", "WARN", {})

def _remove_lock(cfg_dir: Path) -> None:
    try:
        p = cfg_dir / LOCK_FILENAME
        if p.exists():
            p.unlink()
    except Exception:
        pass

def _run_migrations(cfg_dir: Path) -> Dict[str, Any]:
    """
    Placeholder for migration logic. Each migration should be idempotent and
    write an entry to migrations.log. This function returns migration status.
    """
    migrations_log = cfg_dir / MIGRATIONS_LOG
    status = {"migrations_run": [], "status": "none"}
    # Example: read a version from config.yaml and apply migrations if needed
    try:
        cfg_yaml = cfg_dir / "config.yaml"
        if cfg_yaml.exists() and yaml:
            data = yaml.safe_load(cfg_yaml.read_text(encoding="utf-8"))
            version = data.get("version", 1)
            # Example migration stub: if version < 2, run migration_1_to_2
            if version < 2:
                # perform migration steps here (idempotent)
                # write migration entry
                with open(migrations_log, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"ts": time.time(), "migration": "1->2", "status": "applied"}) + "\n")
                status["migrations_run"].append("1->2")
                status["status"] = "applied"
    except Exception:
        _emit_event("migration_failed", "ERROR", {})
        status["status"] = "failed"
    return status

# Public API
_resolved_cache: Optional[Path] = None

def resolve(auto_repair: bool = False, prefer_repo_fallback: bool = False) -> Path:
    """
    Resolve and return the canonical config directory Path.
    - auto_repair: if True, attempt self-heal actions (restore/generate placeholders)
    - prefer_repo_fallback: if True, allow creating/using repo .fcc even if user home exists
    """
    global _resolved_cache
    if _resolved_cache:
        return _resolved_cache

    # 1) explicit override
    env = os.environ.get("FCC_CONFIG_DIR")
    if env:
        p = Path(env)
        _ensure_dir(p)
        _emit_event("resolved", "INFO", {"method": "env_override", "path": str(p)})
        _write_lock(p)
        _validate_and_self_heal(p, auto_repair)
        _resolved_cache = p
        os.environ["FCC_CONFIG_DIR"] = str(p)
        return p

    # 2) WSL: prefer Windows user config if present
    if running_in_wsl():
        win_cfg = _windows_user_config_path()
        if win_cfg and win_cfg.exists():
            _emit_event("resolved", "INFO", {"method": "wsl_windows_config", "path": str(win_cfg)})
            _write_lock(win_cfg)
            _validate_and_self_heal(win_cfg, auto_repair)
            _resolved_cache = win_cfg
            os.environ["FCC_CONFIG_DIR"] = str(win_cfg)
            return win_cfg

    # 3) platform default
    user_cfg = _platform_user_config()
    if user_cfg.exists() and not prefer_repo_fallback:
        _emit_event("resolved", "INFO", {"method": "platform_user_config", "path": str(user_cfg)})
        _write_lock(user_cfg)
        _validate_and_self_heal(user_cfg, auto_repair)
        _resolved_cache = user_cfg
        os.environ["FCC_CONFIG_DIR"] = str(user_cfg)
        return user_cfg

    # 4) repo fallback (only if present or explicitly allowed)
    repo_cfg = _repo_fallback_config()
    if repo_cfg.exists() or prefer_repo_fallback:
        _ensure_dir(repo_cfg)
        _emit_event("resolved", "INFO", {"method": "repo_fallback", "path": str(repo_cfg)})
        _write_lock(repo_cfg)
        _validate_and_self_heal(repo_cfg, auto_repair)
        _resolved_cache = repo_cfg
        os.environ["FCC_CONFIG_DIR"] = str(repo_cfg)
        return repo_cfg

    # 5) create defaults at platform default
    _ensure_dir(user_cfg)
    _create_defaults(user_cfg)
    _emit_event("resolved", "INFO", {"method": "created_defaults", "path": str(user_cfg)})
    _write_lock(user_cfg)
    _validate_and_self_heal(user_cfg, auto_repair)
    _resolved_cache = user_cfg
    os.environ["FCC_CONFIG_DIR"] = str(user_cfg)
    return user_cfg

def _create_defaults(cfg_dir: Path) -> None:
    """
    Copy templates into cfg_dir for any missing default files.
    """
    _ensure_dir(cfg_dir)
    for fname in DEFAULT_FILES:
        dst = cfg_dir / fname
        if dst.exists():
            continue
        tpl = TEMPLATES_DIR / fname
        try:
            if tpl.exists():
                shutil.copy(str(tpl), str(dst))
                _emit_event("copied_template", "INFO", {"file": fname})
            else:
                # create minimal placeholder
                if fname.endswith(".json"):
                    dst.write_text("{}", encoding="utf-8")
                else:
                    dst.write_text("# default\n", encoding="utf-8")
                _emit_event("created_placeholder", "INFO", {"file": fname})
        except Exception as e:
            _emit_event("create_default_failed", "ERROR", {"file": fname, "error": str(e)})

def get_config_dir() -> Path:
    """
    Convenience getter: returns resolved config dir, resolving if necessary.
    """
    return resolve()

# Clean-up helper (call on shutdown if desired)
def cleanup() -> None:
    try:
        cfg = _resolved_cache or Path(os.environ.get("FCC_CONFIG_DIR") or "")
        if cfg:
            _remove_lock(Path(cfg))
    except Exception:
        pass

# If module imported at runtime, do not auto-repair by default; just resolve
if __name__ != "__main__":
    try:
        # Resolve but do not auto-repair unless env var set
        auto = os.environ.get("FCC_AUTO_REPAIR", "false").lower() in ("1", "true", "yes")
        prefer_repo = os.environ.get("FCC_ALLOW_REPO_FALLBACK", "false").lower() in ("1", "true", "yes")
        resolve(auto_repair=auto, prefer_repo_fallback=prefer_repo)
    except Exception:
        LOG.exception("env_resolver initialization failed")
