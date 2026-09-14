import os
from pathlib import Path

def test_resolve_runs(tmp_path, monkeypatch):
    # ensure resolver can create defaults in a temp HOME
    monkeypatch.setenv("HOME", str(tmp_path))
    from free_claude_code.config import env_resolver
    cfg = env_resolver.resolve()
    assert cfg.exists()
    for f in ["config.yaml", "providers.json", "secrets.json", "admin.json"]:
        assert (cfg / f).exists()
