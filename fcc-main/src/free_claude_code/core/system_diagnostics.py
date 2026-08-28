"""System-level diagnostics for Free Claude Code.

Provides tri-layer diagnostics:

- Machine-side: OS, hardware, environment, toolchains.
- Server-side: FCC runtime, monitors, admin UI, health endpoints.
- Shell/program-side: shells, Python/Node/Rust environments, PATH, CLIs.

Acts as the public interface to core.dependency_resolver.resolve_dependencies().
"""

from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Optional

from .dependency_resolver import resolve_dependencies

try:
    from .monitoring import start_monitoring_orchestrator  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    start_monitoring_orchestrator = None  # type: ignore[assignment]

try:
    from .logging_integration import log_with_context  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    def log_with_context(message: str, level: str = "info", **context: Any) -> None:  # type: ignore[func-returns-value]
        return


try:
    from .trace import trace_event  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    def trace_event(event: str, **fields: Any) -> None:  # type: ignore[func-returns-value]
        return


DiagnosticDomain = Literal["machine", "server", "shell"]
DiagnosticSeverity = Literal["low", "medium", "high"]
DiagnosticConfidence = Literal["low", "medium", "high"]


@dataclass(frozen=True, slots=True)
class SystemPlatformInfo:
    """Basic platform identification for FCC system diagnostics."""

    os_name: str
    os_version: str | None
    is_windows: bool
    is_linux: bool
    is_wsl: bool
    is_mac: bool
    distro_name: str | None
    shell: str | None
    cpu_model: str | None
    cpu_cores: int | None
    total_ram_bytes: int | None


@dataclass(frozen=True, slots=True)
class ToolPresence:
    """Presence and basic resolution of a tool in PATH."""

    name: str
    found: bool
    path: str | None


@dataclass(frozen=True, slots=True)
class DiagnosticIssue:
    """Curated diagnostic issue with severity, domain, and suggested fix."""

    id: str
    domain: DiagnosticDomain
    severity: DiagnosticSeverity
    confidence: DiagnosticConfidence
    title: str
    description: str
    suggested_fix: str | None = None
    related_tools: tuple[str, ...] = ()
    related_env: tuple[str, ...] = ()
    raw_data: Any | None = None


@dataclass(frozen=True, slots=True)
class SystemDiagnosticsSummary:
    """High-level summary of system diagnostics for orchestrator and UI."""

    platform: SystemPlatformInfo
    tools: list[ToolPresence]
    has_gpu: bool
    machine_issues: list[DiagnosticIssue]
    server_issues: list[DiagnosticIssue]
    shell_issues: list[DiagnosticIssue]
    resolver_plan: Any  # ResolutionPlan from dependency_resolver


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------


def _detect_wsl() -> bool:
    """Best-effort WSL detection without hard failure."""
    try:
        if "WSL_INTEROP" in os.environ:
            return True
        uname = platform.uname()
        rel = uname.release.lower()
        if "microsoft" in rel or "wsl" in rel:
            return True
    except Exception:
        pass
    return False


def _detect_distro() -> str | None:
    """Best-effort Linux distro detection."""
    if platform.system().lower() != "linux":
        return None

    # Try /etc/os-release
    try:
        os_release = "/etc/os-release"
        if os.path.exists(os_release):
            data: dict[str, str] = {}
            with open(os_release, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    data[key] = value.strip().strip('"')
            for key in ("PRETTY_NAME", "NAME"):
                if key in data and data[key]:
                    return data[key]
    except Exception:
        pass

    # Fallback: lsb_release
    try:
        out = subprocess.check_output(
            ["lsb_release", "-d"], stderr=subprocess.DEVNULL, text=True
        )
        if ":" in out:
            return out.split(":", 1)[1].strip()
        return out.strip() or None
    except Exception:
        return None


def _detect_shell() -> str | None:
    """Best-effort shell detection."""
    if os.name == "nt":
        comspec = os.environ.get("COMSPEC")
        if comspec:
            return os.path.basename(comspec)
        if shutil.which("powershell"):
            return "powershell"
        if shutil.which("pwsh"):
            return "pwsh"
        return "cmd"

    shell = os.environ.get("SHELL")
    if shell:
        return os.path.basename(shell)
    return None


def _detect_cpu_model() -> str | None:
    """Best-effort CPU model detection."""
    try:
        if platform.system().lower() == "windows":
            return platform.processor() or None
        if platform.system().lower() == "linux":
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "model name" in line.lower():
                        return line.split(":", 1)[1].strip()
        if platform.system().lower() == "darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            return out.strip() or None
    except Exception:
        return None
    return None


def _detect_cpu_cores() -> int | None:
    try:
        return os.cpu_count()
    except Exception:
        return None


def _detect_total_ram_bytes() -> int | None:
    """Best-effort total RAM detection."""
    try:
        if platform.system().lower() == "linux":
            with open("/proc/meminfo", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        parts = line.split()
                        if len(parts) >= 2:
                            # kB to bytes
                            return int(parts[1]) * 1024
        if platform.system().lower() == "darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            return int(out.strip())
        if platform.system().lower() == "windows":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):  # type: ignore[valid-type]
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
                return int(stat.ullTotalPhys)
    except Exception:
        return None
    return None


def get_platform_info() -> SystemPlatformInfo:
    """Return basic platform information for system diagnostics."""
    system = platform.system().lower()
    is_windows = system == "windows"
    is_linux = system == "linux"
    is_mac = system == "darwin"
    is_wsl = _detect_wsl()

    try:
        os_version = platform.version()
    except Exception:
        os_version = None

    distro_name = _detect_distro() if is_linux else None
    shell = _detect_shell()
    cpu_model = _detect_cpu_model()
    cpu_cores = _detect_cpu_cores()
    total_ram_bytes = _detect_total_ram_bytes()

    return SystemPlatformInfo(
        os_name=platform.system(),
        os_version=os_version,
        is_windows=is_windows,
        is_linux=is_linux,
        is_wsl=is_wsl,
        is_mac=is_mac,
        distro_name=distro_name,
        shell=shell,
        cpu_model=cpu_model,
        cpu_cores=cpu_cores,
        total_ram_bytes=total_ram_bytes,
    )


# ---------------------------------------------------------------------------
# Tool presence checks
# ---------------------------------------------------------------------------


def _check_tool(name: str) -> ToolPresence:
    """Check whether a tool is present in PATH."""
    try:
        path = shutil.which(name)
        return ToolPresence(name=name, found=bool(path), path=path)
    except Exception:
        return ToolPresence(name=name, found=False, path=None)


def check_tools(names: Iterable[str]) -> list[ToolPresence]:
    """Check a list of tools for presence in PATH."""
    return [_check_tool(n) for n in names]


def get_default_tool_list() -> list[str]:
    """Default tool list for system diagnostics."""
    return [
        "python",
        "python3",
        "pip",
        "node",
        "npm",
        "rustc",
        "cargo",
        "maturin",
        "bash",
        "sh",
        "powershell",
        "pwsh",
        "git",
    ]


# ---------------------------------------------------------------------------
# GPU detection (best-effort)
# ---------------------------------------------------------------------------


def _has_nvidia_smi() -> bool:
    try:
        return shutil.which("nvidia-smi") is not None
    except Exception:
        return False


def _has_rocm_smi() -> bool:
    try:
        return shutil.which("rocm-smi") is not None
    except Exception:
        return False


def _has_directml_hint() -> bool:
    try:
        if os.name == "nt":
            for env_key in ("DIRECTML_PATH", "DML_DEBUG", "DML_ENABLE"):
                if env_key in os.environ:
                    return True
        return False
    except Exception:
        return False


def detect_gpu_presence() -> bool:
    """Best-effort GPU presence detection."""
    if _has_nvidia_smi():
        return True
    if _has_rocm_smi():
        return True
    if _has_directml_hint():
        return True
    return False


# ---------------------------------------------------------------------------
# Machine-side issue detection
# ---------------------------------------------------------------------------


def _issue_missing_tool(name: str, domain: DiagnosticDomain = "machine") -> DiagnosticIssue:
    return DiagnosticIssue(
        id=f"missing_tool:{name}",
        domain=domain,
        severity="medium",
        confidence="high",
        title=f"Missing tool: {name}",
        description=f"The tool '{name}' was not found in PATH.",
        suggested_fix=f"Install '{name}' and ensure it is available in PATH.",
        related_tools=(name,),
    )


def _issue_no_gpu() -> DiagnosticIssue:
    return DiagnosticIssue(
        id="gpu:missing",
        domain="machine",
        severity="low",
        confidence="medium",
        title="No GPU detected",
        description=(
            "No CUDA/ROCm/DirectML GPU was detected. FCC can still run, "
            "but GPU-accelerated workloads may be unavailable."
        ),
        suggested_fix="Install GPU drivers and toolchains if GPU acceleration is desired.",
    )


def _issue_low_ram(total_ram_bytes: Optional[int]) -> Optional[DiagnosticIssue]:
    if total_ram_bytes is None:
        return None
    # Heuristic: < 8 GiB is low for heavy workloads
    if total_ram_bytes < 8 * 1024 * 1024 * 1024:
        return DiagnosticIssue(
            id="ram:low",
            domain="machine",
            severity="medium",
            confidence="high",
            title="Low system RAM",
            description=(
                "Total system RAM appears to be below 8 GiB. "
                "Heavy FCC workloads may be constrained."
            ),
            suggested_fix="Consider upgrading RAM or reducing concurrent workloads.",
            raw_data={"total_ram_bytes": total_ram_bytes},
        )
    return None


def detect_machine_issues(
    platform_info: SystemPlatformInfo,
    tools: list[ToolPresence],
    has_gpu: bool,
) -> list[DiagnosticIssue]:
    issues: list[DiagnosticIssue] = []

    missing = [t for t in tools if not t.found]
    for t in missing:
        issues.append(_issue_missing_tool(t.name, domain="machine"))

    if not has_gpu:
        issues.append(_issue_no_gpu())

    ram_issue = _issue_low_ram(platform_info.total_ram_bytes)
    if ram_issue is not None:
        issues.append(ram_issue)

    return issues


# ---------------------------------------------------------------------------
# Server-side diagnostics (best-effort)
# ---------------------------------------------------------------------------


def _check_tcp_port(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _issue_server_unreachable(port: int) -> DiagnosticIssue:
    return DiagnosticIssue(
        id=f"server:unreachable:{port}",
        domain="server",
        severity="high",
        confidence="medium",
        title="FCC server not reachable",
        description=f"FCC server is not reachable on localhost:{port}.",
        suggested_fix="Ensure the FCC server is running and listening on the expected port.",
        raw_data={"port": port},
    )


def _issue_monitoring_not_started() -> DiagnosticIssue:
    return DiagnosticIssue(
        id="monitoring:not_started",
        domain="server",
        severity="low",
        confidence="medium",
        title="Monitoring orchestrator not started",
        description=(
            "The monitoring orchestrator does not appear to be active. "
            "This does not block FCC, but monitoring features may be unavailable."
        ),
        suggested_fix="Start the monitoring orchestrator via CLI or bootstrap hooks.",
    )


def detect_server_issues(
    expected_server_port: Optional[int] = None,
    monitoring_expected: bool = True,
) -> list[DiagnosticIssue]:
    issues: list[DiagnosticIssue] = []

    if expected_server_port is not None:
        if not _check_tcp_port("127.0.0.1", expected_server_port, timeout=0.5):
            issues.append(_issue_server_unreachable(expected_server_port))

    if monitoring_expected and start_monitoring_orchestrator is None:
        issues.append(_issue_monitoring_not_started())

    return issues


# ---------------------------------------------------------------------------
# Shell / program-side diagnostics
# ---------------------------------------------------------------------------


def _issue_missing_shell(shell_name: str) -> DiagnosticIssue:
    return DiagnosticIssue(
        id=f"shell:missing:{shell_name}",
        domain="shell",
        severity="medium",
        confidence="high",
        title=f"Missing shell: {shell_name}",
        description=f"The shell '{shell_name}' was not found.",
        suggested_fix=f"Install '{shell_name}' or configure FCC to use an available shell.",
        related_tools=(shell_name,),
    )


def _issue_python_env_mismatch() -> DiagnosticIssue:
    return DiagnosticIssue(
        id="python:env_mismatch",
        domain="shell",
        severity="medium",
        confidence="medium",
        title="Python environment mismatch",
        description=(
            "Python executable and environment may not match FCC expectations. "
            "This can cause dependency or runtime issues."
        ),
        suggested_fix=(
            "Ensure FCC is running in the intended virtual environment and that "
            "python/pip refer to the same interpreter."
        ),
    )


def detect_shell_issues(
    platform_info: SystemPlatformInfo,
    tools: list[ToolPresence],
) -> list[DiagnosticIssue]:
    issues: list[DiagnosticIssue] = []

    if platform_info.shell is None:
        issues.append(
            DiagnosticIssue(
                id="shell:unknown",
                domain="shell",
                severity="low",
                confidence="medium",
                title="Shell not detected",
                description="No active shell could be detected from environment.",
                suggested_fix="Ensure SHELL or COMSPEC is set appropriately.",
            )
        )
    else:
        # If shell is bash/zsh/fish and missing in tools, flag it.
        shell_name = platform_info.shell
        if shell_name in ("bash", "zsh", "fish"):
            if not any(t.name == shell_name and t.found for t in tools):
                issues.append(_issue_missing_shell(shell_name))

    # Simple heuristic: if python and python3 disagree or pip is missing, flag.
    python = next((t for t in tools if t.name == "python" and t.found), None)
    python3 = next((t for t in tools if t.name == "python3" and t.found), None)
    pip = next((t for t in tools if t.name == "pip" and t.found), None)

    if (python or python3) and not pip:
        issues.append(
            DiagnosticIssue(
                id="python:pip_missing",
                domain="shell",
                severity="medium",
                confidence="high",
                title="pip missing for Python",
                description="Python is present but pip is not available.",
                suggested_fix="Install pip for the active Python interpreter.",
                related_tools=("python", "python3", "pip"),
            )
        )

    if python and python3 and python.path != python3.path:
        issues.append(_issue_python_env_mismatch())

    return issues


# ---------------------------------------------------------------------------
# Resolver integration
# ---------------------------------------------------------------------------


def diagnose_system(
    expected_server_port: Optional[int] = None,
    monitoring_expected: bool = True,
) -> SystemDiagnosticsSummary:
    """Run full tri-layer system diagnostics including dependency resolver.

    This is the primary entrypoint for orchestrator and admin UI.
    """
    trace_event("diagnostics:start")

    platform_info = get_platform_info()
    tools = check_tools(get_default_tool_list())
    has_gpu = detect_gpu_presence()

    machine_issues = detect_machine_issues(platform_info, tools, has_gpu)
    server_issues = detect_server_issues(
        expected_server_port=expected_server_port,
        monitoring_expected=monitoring_expected,
    )
    shell_issues = detect_shell_issues(platform_info, tools)

    try:
        resolver_plan = resolve_dependencies()
    except Exception as exc:  # noqa: BLE001
        log_with_context(
            "Dependency resolver failed during system diagnostics.",
            level="error",
            error=str(exc),
        )
        resolver_plan = {
            "error": str(exc),
            "plan": None,
        }

    summary = SystemDiagnosticsSummary(
        platform=platform_info,
        tools=tools,
        has_gpu=has_gpu,
        machine_issues=machine_issues,
        server_issues=server_issues,
        shell_issues=shell_issues,
        resolver_plan=resolver_plan,
    )

    trace_event("diagnostics:complete", issues=len(machine_issues) + len(server_issues) + len(shell_issues))
    return summary


# ---------------------------------------------------------------------------
# Mode-specific convenience wrappers
# ---------------------------------------------------------------------------


def diagnose_machine_only() -> SystemDiagnosticsSummary:
    """Run machine-side diagnostics only, still returning a full summary."""
    platform_info = get_platform_info()
    tools = check_tools(get_default_tool_list())
    has_gpu = detect_gpu_presence()

    machine_issues = detect_machine_issues(platform_info, tools, has_gpu)
    server_issues: list[DiagnosticIssue] = []
    shell_issues: list[DiagnosticIssue] = []

    try:
        resolver_plan = resolve_dependencies()
    except Exception as exc:  # noqa: BLE001
        resolver_plan = {"error": str(exc), "plan": None}

    return SystemDiagnosticsSummary(
        platform=platform_info,
        tools=tools,
        has_gpu=has_gpu,
        machine_issues=machine_issues,
        server_issues=server_issues,
        shell_issues=shell_issues,
        resolver_plan=resolver_plan,
    )


def diagnose_server_only(expected_server_port: Optional[int] = None) -> list[DiagnosticIssue]:
    """Run server-side diagnostics only."""
    return detect_server_issues(expected_server_port=expected_server_port, monitoring_expected=True)


def diagnose_shell_only() -> list[DiagnosticIssue]:
    """Run shell/program-side diagnostics only."""
    platform_info = get_platform_info()
    tools = check_tools(get_default_tool_list())
    return detect_shell_issues(platform_info, tools)


# ---------------------------------------------------------------------------
# Resolution plan helpers
# ---------------------------------------------------------------------------


def get_resolution_plan() -> Any:
    """Return the raw ResolutionPlan from dependency_resolver."""
    return resolve_dependencies()


def get_environment_issues() -> list[Any]:
    """Return environment issues from the resolver plan."""
    plan = resolve_dependencies()
    return getattr(plan, "env_issues", [])


def get_missing_dependencies() -> list[Any]:
    """Return missing dependencies from the resolver plan."""
    plan = resolve_dependencies()
    return getattr(plan, "missing_dependencies", [])


def get_outdated_dependencies() -> list[Any]:
    """Return outdated dependencies from the resolver plan."""
    plan = resolve_dependencies()
    return getattr(plan, "outdated_dependencies", [])


def get_suggested_tasks() -> list[Any]:
    """Return suggested admin tasks from the resolver plan."""
    plan = resolve_dependencies()
    return getattr(plan, "suggested_tasks", [])


# ---------------------------------------------------------------------------
# JSON-friendly export helpers
# ---------------------------------------------------------------------------


def _issue_to_dict(issue: DiagnosticIssue) -> dict[str, Any]:
    return {
        "id": issue.id,
        "domain": issue.domain,
        "severity": issue.severity,
        "confidence": issue.confidence,
        "title": issue.title,
        "description": issue.description,
        "suggested_fix": issue.suggested_fix,
        "related_tools": list(issue.related_tools),
        "related_env": list(issue.related_env),
        "raw_data": issue.raw_data,
    }


def export_diagnostics_json(summary: SystemDiagnosticsSummary) -> dict[str, Any]:
    """Export diagnostics summary as a JSON-friendly dict."""
    return {
        "platform": {
            "os_name": summary.platform.os_name,
            "os_version": summary.platform.os_version,
            "is_windows": summary.platform.is_windows,
            "is_linux": summary.platform.is_linux,
            "is_wsl": summary.platform.is_wsl,
            "is_mac": summary.platform.is_mac,
            "distro_name": summary.platform.distro_name,
            "shell": summary.platform.shell,
            "cpu_model": summary.platform.cpu_model,
            "cpu_cores": summary.platform.cpu_cores,
            "total_ram_bytes": summary.platform.total_ram_bytes,
        },
        "tools": [
            {"name": t.name, "found": t.found, "path": t.path}
            for t in summary.tools
        ],
        "has_gpu": summary.has_gpu,
        "machine_issues": [_issue_to_dict(i) for i in summary.machine_issues],
        "server_issues": [_issue_to_dict(i) for i in summary.server_issues],
        "shell_issues": [_issue_to_dict(i) for i in summary.shell_issues],
        "resolver_plan": summary.resolver_plan,
    }


# ---------------------------------------------------------------------------
# Simple CLI entrypoint (optional)
# ---------------------------------------------------------------------------


def cli_diagnose_all(
    expected_server_port: Optional[int] = None,
    monitoring_expected: bool = True,
) -> None:
    """Simple CLI-oriented diagnostic runner."""
    summary = diagnose_system(
        expected_server_port=expected_server_port,
        monitoring_expected=monitoring_expected,
    )

    print("=== Platform ===")
    print(f"OS: {summary.platform.os_name} {summary.platform.os_version}")
    if summary.platform.distro_name:
        print(f"Distro: {summary.platform.distro_name}")
    print(f"Shell: {summary.platform.shell}")
    print(f"CPU: {summary.platform.cpu_model} ({summary.platform.cpu_cores} cores)")
    print(f"RAM: {summary.platform.total_ram_bytes} bytes")
    print(f"GPU present: {summary.has_gpu}")
    print()

    def _print_issues(label: str, issues: list[DiagnosticIssue]) -> None:
        print(f"=== {label} ({len(issues)}) ===")
        for issue in issues:
            print(f"- [{issue.domain}/{issue.severity}] {issue.title}")
            print(f"  {issue.description}")
            if issue.suggested_fix:
                print(f"  Fix: {issue.suggested_fix}")
        print()

    _print_issues("Machine issues", summary.machine_issues)
    _print_issues("Server issues", summary.server_issues)
    _print_issues("Shell issues", summary.shell_issues)

    print("=== Resolver Plan (summary) ===")
    if isinstance(summary.resolver_plan, dict) and "error" in summary.resolver_plan:
        print(f"Resolver error: {summary.resolver_plan['error']}")
    else:
        print("Resolver plan available (see admin UI or logs for details).")

    time.sleep(0.01)
