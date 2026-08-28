#!/usr/bin/env python3
"""
FCC Integrity Scanner (v2)
Smarter import analysis, FCC-aware module filtering,
provider folder validation, test path checks, and
real external dependency detection.
"""

import ast
import importlib
import os
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "free_claude_code"
TESTS = ROOT / "tests"
PYPROJECT = ROOT / "pyproject.toml"

# FCC internal top-level namespaces
FCC_INTERNAL = {
    "free_claude_code",
    "runtime",
    "messaging",
    "api",
    "cli",
    "core",
    "providers",
    "adapters",
    "desktop",
    "wizard",
    "config",
    "utils",
}

# FCC provider folders expected
FCC_PROVIDER_FOLDERS = {
    "anthropic",
    "openai_responses",
    "fcc-anthropic",  # legacy name
    "mistral",
    "groq",
    "cohere",
    "xai",
    "llm7",
    "google",
}


def load_pyproject_dependencies() -> set[str]:
    if not PYPROJECT.is_file():
        print(f"[ERROR] pyproject.toml not found at {PYPROJECT}")
        return set()
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    deps = set()
    for dep in data.get("project", {}).get("dependencies", []):
        name = dep.split("[", 1)[0].split(" ", 1)[0].split(">=", 1)[0].split("==", 1)[0]
        deps.add(name.lower())
    return deps


def walk_python_files(root: Path) -> list[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in filenames:
            if f.endswith(".py"):
                files.append(Path(dirpath) / f)
    return files


def collect_imports(py_file: Path) -> set[str]:
    text = py_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(py_file))
    except SyntaxError as e:
        print(f"[WARN] Syntax error in {py_file}: {e}")
        return set()
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module.split(".", 1)[0])
    return modules


def check_missing_external_modules(imports: set[str], deps: set[str]) -> set[str]:
    missing = set()
    for mod in sorted(imports):
        # Skip FCC internal modules
        if mod in FCC_INTERNAL:
            continue
        # Skip stdlib-ish
        if mod in {"sys", "os", "typing", "collections", "pathlib"}:
            continue
        # Skip installed deps
        if mod.lower() in deps:
            continue
        # Try import
        try:
            importlib.import_module(mod)
        except Exception:
            missing.add(mod)
    return missing


def check_provider_folders(root: Path) -> list[str]:
    issues = []
    core = root / "core"
    if not core.is_dir():
        issues.append("[ERROR] core folder missing")
        return issues
    existing = {p.name for p in core.iterdir() if p.is_dir()}
    for expected in FCC_PROVIDER_FOLDERS:
        if expected not in existing:
            issues.append(f"[WARN] provider folder missing: {expected}")
    return issues


def check_package_structure(root: Path) -> list[str]:
    issues = []
    for dirpath, dirnames, filenames in os.walk(root):
        p = Path(dirpath)
        if "__pycache__" in dirnames:
            dirnames.remove("__pycache__")
        if any(f.endswith(".py") for f in filenames) and "__init__.py" not in filenames:
            rel = p.relative_to(ROOT)
            issues.append(f"[WARN] missing __init__.py in: {rel}")
    return issues


def check_tests() -> list[str]:
    issues = []
    if not TESTS.exists():
        issues.append("[WARN] tests folder missing")
        return issues
    py_files = list(TESTS.glob("**/*.py"))
    if not py_files:
        issues.append("[WARN] no test files found")
    return issues


def main():
    print("=== FCC Integrity Scan v2 ===")
    print(f"Root: {ROOT}")
    print(f"Package: {SRC}\n")

    deps = load_pyproject_dependencies()
    print(f"[INFO] pyproject dependencies ({len(deps)}):")
    for d in sorted(deps):
        print(f"  - {d}")
    print()

    if not SRC.is_dir():
        print(f"[ERROR] src/free_claude_code not found at {SRC}")
        sys.exit(1)

    files = walk_python_files(SRC)
    print(f"[INFO] Python files found: {len(files)}\n")

    all_imports = set()
    for f in files:
        all_imports.update(collect_imports(f))

    print(f"[INFO] Unique imported modules ({len(all_imports)}):")
    for m in sorted(all_imports):
        print(f"  - {m}")
    print()

    missing_external = check_missing_external_modules(all_imports, deps)
    if missing_external:
        print("[ERROR] Missing external dependencies:")
        for m in sorted(missing_external):
            print(f"  - {m}")
        print()
    else:
        print("[OK] No missing external dependencies.\n")

    provider_issues = check_provider_folders(SRC)
    if provider_issues:
        print("[PROVIDERS] Issues detected:")
        for msg in provider_issues:
            print(msg)
        print()
    else:
        print("[OK] All provider folders present.\n")

    struct_issues = check_package_structure(SRC)
    if struct_issues:
        print("[STRUCTURE] Issues detected:")
        for msg in struct_issues:
            print(msg)
        print()
    else:
        print("[OK] Package structure looks good.\n")

    test_issues = check_tests()
    if test_issues:
        print("[TESTS] Issues detected:")
        for msg in test_issues:
            print(msg)
        print()
    else:
        print("[OK] Tests folder looks good.\n")

    print("=== Scan complete ===")


if __name__ == "__main__":
    main()
