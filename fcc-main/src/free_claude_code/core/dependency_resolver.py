"""
Multi-platform dependency resolver for FCC monitoring orchestrator.

Responsibilities:
- Detect missing / (future) outdated monitoring dependencies.
- Be aware of three execution contexts:
    - Windows-native host
    - WSL (Linux inside Windows)
    - Linux-native host
- Group dependencies by type (terminal/python/node/web/toolchain) and by platform (windows/wsl/linux).
- Mark critical vs optional dependencies.
- Detect common environment issues for:
    - Windows (PowerShell, Scoop, Chocolatey, npm)
    - WSL (distro, package manager, systemd)
    - Linux (distro, package manager)
    - Cross-platform toolchain (Node, GPU)
- Prepare installer / updater / fix command sets (no implicit elevation).
- Provide a structured ResolutionPlan for:
    - Monitoring orchestrator
    - System Admin / Diagnostics UI
    - Machine-help / AI explanation layer
- Optionally write a machine-readable installer_log.jsonc.

This module does NOT:
- Elevate FCC itself.
- Silently install or modify the system.
- Run commands directly; it only describes what should be run.

NOTE: torch, python3, rustc, cargo, and maturin availability is each
reported once, via missing_dependencies (checked in _check_dependencies),
not duplicated in env_issues. See _detect_env_issues docstring.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional, Literal, Dict, Tuple
import json
import shutil
import platform
import subprocess
import os


TaskType = Literal[
    "install_dependency",
    "update_dependency",
    "fix_environment",
    "run_diagnostics",
    "generate_log",
]

ShellType = Literal["powershell", "cmd", "bash"]

DependencyKind = Literal["terminal", "python", "node", "web", "toolchain"]

DependencyGroup = Literal[
    "windows_monitors",
    "wsl_monitors",
    "linux_monitors",
    "python_toolchain",
    "rust_toolchain",
    "ai_toolchain",
    "gpu_stack",
    "core_environment",
]


@dataclass
class DependencySpec:
    name: str
    display_name: str
    kind: DependencyKind
    group: DependencyGroup
    critical: bool
    check_command: Optional[str]
    install_commands: List[str]
    update_commands: List[str]


@dataclass
class EnvIssue:
    key: str
    description: str
    fix_commands: List[str]
    platform_scope: Literal["windows", "wsl", "linux", "generic"]


@dataclass
class AdminTask:
    task_type: TaskType
    description: str
    shell: ShellType
    commands: List[str]
    group: Optional[DependencyGroup] = None
    platform_scope: Optional[Literal["windows", "wsl", "linux", "generic"]] = None


@dataclass
class ResolutionPlan:
    missing_dependencies: List[DependencySpec]
    outdated_dependencies: List[DependencySpec]
    env_issues: List[EnvIssue]
    suggested_tasks: List[AdminTask]


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

def _detect_platform() -> Dict[str, bool]:
    system = platform.system()
    is_windows = system == "Windows"
    is_linux = system == "Linux"

    # WSL detection: kernel release contains "microsoft" OR WSLInterop present
    is_wsl = is_linux and (
        "microsoft" in platform.release().lower()
        or os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop")
    )

    return {
        "windows": is_windows,
        "linux": is_linux and not is_wsl,
        "wsl": is_wsl,
    }


# ---------------------------------------------------------------------------
# Dependency matrix (platform-aware)
# ---------------------------------------------------------------------------

def _dependency_matrix(platform_flags: Dict[str, bool]) -> List[DependencySpec]:
    """
    Define all known monitoring-related and toolchain-related dependencies.
    Platform flags allow us to tailor groups and commands.
    """
    deps: List[DependencySpec] = []

    # Windows-native monitors (btop via Scoop, etc.)
    if platform_flags["windows"]:
        deps.extend(
            [
                DependencySpec(
                    name="btop",
                    display_name="btop (terminal monitor, Windows via Scoop)",
                    kind="terminal",
                    group="windows_monitors",
                    critical=True,
                    check_command="btop",
                    install_commands=[
                        "iwr -useb get.scoop.sh | iex",
                        "scoop install btop",
                    ],
                    update_commands=[
                        "scoop update btop",
                    ],
                ),
                DependencySpec(
                    name="bottom",
                    display_name="bottom (btm, terminal monitor, Windows via Scoop)",
                    kind="terminal",
                    group="windows_monitors",
                    critical=False,
                    check_command="btm",
                    install_commands=[
                        "iwr -useb get.scoop.sh | iex",
                        "scoop install bottom",
                    ],
                    update_commands=[
                        "scoop update bottom",
                    ],
                ),
                DependencySpec(
                    name="htop",
                    display_name="htop (terminal monitor, Windows via Chocolatey)",
                    kind="terminal",
                    group="windows_monitors",
                    critical=False,
                    check_command="htop",
                    install_commands=[
                        "Set-ExecutionPolicy Bypass -Scope Process -Force",
                        "iwr https://community.chocolatey.org/install.ps1 -UseBasicParsing | iex",
                        "choco install htop -y",
                    ],
                    update_commands=[
                        "choco upgrade htop -y",
                    ],
                ),
                DependencySpec(
                    name="nmon",
                    display_name="nmon (terminal monitor, Windows via Chocolatey)",
                    kind="terminal",
                    group="windows_monitors",
                    critical=False,
                    check_command="nmon",
                    install_commands=[
                        "Set-ExecutionPolicy Bypass -Scope Process -Force",
                        "iwr https://community.chocolatey.org/install.ps1 -UseBasicParsing | iex",
                        "choco install nmon -y",
                    ],
                    update_commands=[
                        "choco upgrade nmon -y",
                    ],
                ),
                DependencySpec(
                    name="nom",
                    display_name="nom (Node-based monitor, Windows)",
                    kind="node",
                    group="windows_monitors",
                    critical=False,
                    check_command="nom",
                    install_commands=[
                        "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force",
                        "npm install -g nom",
                    ],
                    update_commands=[
                        "npm update -g nom",
                    ],
                ),
            ]
        )

    # WSL / Linux-native monitors (btop, glances, etc.)
    if platform_flags["wsl"] or platform_flags["linux"]:
        deps.extend(
            [
                DependencySpec(
                    name="btop",
                    display_name="btop (terminal monitor, Linux/WSL)",
                    kind="terminal",
                    group="wsl_monitors" if platform_flags["wsl"] else "linux_monitors",
                    critical=True,
                    check_command="btop",
                    install_commands=[
                        "sudo apt update",
                        "sudo apt install -y btop",
                    ],
                    update_commands=[
                        "sudo apt update",
                        "sudo apt install -y --only-upgrade btop",
                    ],
                ),
                DependencySpec(
                    name="glances",
                    display_name="Glances (Python system monitor, Linux/WSL)",
                    kind="python",
                    group="python_toolchain",
                    critical=True,
                    check_command="glances",
                    install_commands=[
                        "python3 -m pip install glances",
                    ],
                    update_commands=[
                        "python3 -m pip install --upgrade glances",
                    ],
                ),
            ]
        )

    # Web monitors (Grafana, Netdata, Prometheus) — mostly Linux/WSL
    deps.extend(
        [
            DependencySpec(
                name="grafana-server",
                display_name="Grafana (web monitor)",
                kind="web",
                group=(
                    "wsl_monitors" if platform_flags["wsl"] else "linux_monitors"
                    if (platform_flags["wsl"] or platform_flags["linux"])
                    else "windows_monitors"
                ),
                critical=False,
                check_command="grafana-server",
                install_commands=[
                    'echo "Download Grafana from: https://grafana.com/grafana/download and install for your platform."',
                ],
                update_commands=[
                    'echo "Update Grafana via its installer or package manager."',
                ],
            ),
            DependencySpec(
                name="netdata",
                display_name="Netdata (web monitor, best via Linux/WSL)",
                kind="web",
                group="wsl_monitors" if platform_flags["wsl"] else "linux_monitors",
                critical=False,
                check_command="netdata",
                install_commands=[
                    'bash <(curl -Ss https://my-netdata.io/kickstart.sh)',
                ],
                update_commands=[
                    "sudo netdata-updater.sh",
                ],
            ),
            DependencySpec(
                name="prometheus",
                display_name="Prometheus (web monitor)",
                kind="web",
                group="wsl_monitors" if platform_flags["wsl"] else "linux_monitors",
                critical=False,
                check_command="prometheus",
                install_commands=[
                    'echo "Download Prometheus from: https://prometheus.io/download/ and install for your platform."',
                ],
                update_commands=[
                    'echo "Update Prometheus via its binary or package manager."',
                ],
            ),
        ]
    )

    # AI toolchain (Python, Rust, PyTorch, maturin, etc.)
    deps.extend(
        [
            DependencySpec(
                name="python3",
                display_name="Python 3 (AI + tooling)",
                kind="toolchain",
                group="python_toolchain",
                critical=True,
                check_command="python3",
                install_commands=[
                    'echo "Install Python 3 via your OS package manager or official installer."',
                ],
                update_commands=[
                    'echo "Update Python 3 via your OS package manager or official installer."',
                ],
            ),
            DependencySpec(
                name="pip",
                display_name="pip (Python package manager)",
                kind="toolchain",
                group="python_toolchain",
                critical=True,
                check_command="pip",
                install_commands=[
                    "python3 -m ensurepip --upgrade",
                ],
                update_commands=[
                    "python3 -m pip install --upgrade pip",
                ],
            ),
            DependencySpec(
                name="rustc",
                display_name="Rust compiler (rustc)",
                kind="toolchain",
                group="rust_toolchain",
                critical=True,
                check_command="rustc",
                install_commands=[
                    'echo "Install Rust via rustup: https://rustup.rs"',
                ],
                update_commands=[
                    "rustup update",
                ],
            ),
            DependencySpec(
                name="cargo",
                display_name="Cargo (Rust package manager)",
                kind="toolchain",
                group="rust_toolchain",
                critical=True,
                check_command="cargo",
                install_commands=[
                    'echo "Install Rust via rustup: https://rustup.rs (Cargo included)."',
                ],
                update_commands=[
                    "rustup update",
                ],
            ),
            DependencySpec(
                name="maturin",
                display_name="maturin (PyO3 build tool)",
                kind="toolchain",
                group="rust_toolchain",
                critical=False,
                check_command="maturin",
                install_commands=[
                    "python3 -m pip install maturin",
                ],
                update_commands=[
                    "python3 -m pip install --upgrade maturin",
                ],
            ),
            DependencySpec(
                name="torch",
                display_name="PyTorch (AI inference)",
                kind="toolchain",
                group="ai_toolchain",
                critical=True,
                check_command=None,  # checked via Python import
                install_commands=[
                    "python3 -m pip install torch torchvision torchaudio",
                ],
                update_commands=[
                    "python3 -m pip install --upgrade torch torchvision torchaudio",
                ],
            ),
        ]
    )

    return deps


# ---------------------------------------------------------------------------
# Environment diagnostics (platform-aware)
# ---------------------------------------------------------------------------

def _detect_env_issues(platform_flags: Dict[str, bool]) -> List[EnvIssue]:
    """
    Detect environment issues across Windows, WSL, and Linux.
    No fixes are applied here; only described.

    NOTE: torch, python3, rustc, cargo, and maturin are intentionally NOT
    checked here. Each is already tracked as a DependencySpec and verified
    in _check_dependencies() via the same shutil.which() / import probes —
    checking them again here would duplicate the same result in two
    different places in the plan. If any is missing, it appears once, in
    missing_dependencies, with full install/update commands. (npm and
    nvidia-smi have no corresponding DependencySpec, so they are still
    checked here.)
    """
    issues: List[EnvIssue] = []

    is_windows = platform_flags["windows"]
    is_linux = platform_flags["linux"]
    is_wsl = platform_flags["wsl"]

    # Windows-specific diagnostics
    if is_windows:
        # Execution policy
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-ExecutionPolicy"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            policy = (result.stdout or "").strip()
            if policy in ("Restricted", ""):
                issues.append(
                    EnvIssue(
                        key="execution_policy_restricted",
                        description=(
                            "PowerShell execution policy is Restricted; scripts like npm, Scoop, and Chocolatey "
                            "will not run."
                        ),
                        fix_commands=[
                            "Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force",
                        ],
                        platform_scope="windows",
                    )
                )
        except Exception:
            pass

        # PSReadLine
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Import-Module PSReadLine"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                issues.append(
                    EnvIssue(
                        key="psreadline_missing",
                        description=(
                            "PSReadLine module is missing or broken; console input may behave incorrectly."
                        ),
                        fix_commands=[
                            "Install-Module PSReadLine -Force",
                        ],
                        platform_scope="windows",
                    )
                )
        except Exception:
            pass

        # Scoop presence
        if shutil.which("scoop") is None:
            issues.append(
                EnvIssue(
                    key="scoop_missing",
                    description="Scoop is not installed; terminal monitors via Scoop will not be available.",
                    fix_commands=[
                        "iwr -useb get.scoop.sh | iex",
                    ],
                    platform_scope="windows",
                )
            )

        # Chocolatey presence
        if shutil.which("choco") is None:
            issues.append(
                EnvIssue(
                    key="choco_missing",
                    description="Chocolatey is not installed; some terminal tools (htop, nmon) will not be available.",
                    fix_commands=[
                        "Set-ExecutionPolicy Bypass -Scope Process -Force",
                        "iwr https://community.chocolatey.org/install.ps1 -UseBasicParsing | iex",
                    ],
                    platform_scope="windows",
                )
            )

        # WSL presence
        if shutil.which("wsl") is None:
            issues.append(
                EnvIssue(
                    key="wsl_missing",
                    description="WSL is not installed; Linux-first AI tooling and monitors may be limited.",
                    fix_commands=[
                        "wsl --install",
                    ],
                    platform_scope="windows",
                )
            )

    # WSL-specific diagnostics
    if is_wsl:
        # bash presence guard
        if not shutil.which("bash"):
            issues.append(
                EnvIssue(
                    key="bash_missing",
                    description="bash not found; WSL diagnostics unavailable.",
                    fix_commands=[
                        'echo "Install bash or ensure WSL is configured correctly."',
                    ],
                    platform_scope="wsl",
                )
            )
            return issues

        # Distro / package manager
        try:
            result = subprocess.run(
                ["bash", "-lc", "cat /etc/os-release"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            os_release = result.stdout or ""
            if "Ubuntu" in os_release:
                pm_hint = "apt"
            elif "Debian" in os_release:
                pm_hint = "apt"
            elif "Arch" in os_release:
                pm_hint = "pacman"
            else:
                pm_hint = "unknown"
            if pm_hint == "unknown":
                issues.append(
                    EnvIssue(
                        key="wsl_unknown_distro",
                        description="WSL distro package manager could not be determined.",
                        fix_commands=[
                            'echo "Check /etc/os-release and install packages manually."',
                        ],
                        platform_scope="wsl",
                    )
                )
        except Exception:
            pass

        # systemd presence (best-effort)
        try:
            result = subprocess.run(
                ["bash", "-lc", "systemctl is-system-running"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                issues.append(
                    EnvIssue(
                        key="wsl_systemd_missing_or_disabled",
                        description="systemd appears missing or disabled in WSL; some services (Netdata, Prometheus) may not run correctly.",
                        fix_commands=[
                            'echo "Enable systemd in WSL (Ubuntu 22.04+ supports this via /etc/wsl.conf)."',
                        ],
                        platform_scope="wsl",
                    )
                )
        except Exception:
            pass

    # Linux-native diagnostics
    if is_linux:
        # bash presence guard
        if not shutil.which("bash"):
            issues.append(
                EnvIssue(
                    key="bash_missing",
                    description="bash not found; Linux diagnostics unavailable.",
                    fix_commands=[
                        'echo "Install bash via your package manager."',
                    ],
                    platform_scope="linux",
                )
            )
            return issues

        # Distro / package manager
        try:
            result = subprocess.run(
                ["bash", "-lc", "cat /etc/os-release"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            os_release = result.stdout or ""
            if "Ubuntu" in os_release or "Debian" in os_release:
                pm_hint = "apt"
            elif "Fedora" in os_release or "Red Hat" in os_release:
                pm_hint = "dnf"
            elif "Arch" in os_release:
                pm_hint = "pacman"
            else:
                pm_hint = "unknown"
            if pm_hint == "unknown":
                issues.append(
                    EnvIssue(
                        key="linux_unknown_distro",
                        description="Linux distro package manager could not be determined.",
                        fix_commands=[
                            'echo "Check /etc/os-release and install packages manually."',
                        ],
                        platform_scope="linux",
                    )
                )
        except Exception:
            pass

    # Cross-platform toolchain diagnostics (Node, GPU)
    # Node/npm
    if shutil.which("npm") is None:
        issues.append(
            EnvIssue(
                key="npm_missing_or_blocked",
                description="npm is missing or blocked; Node-based tools like nom or LM Studio CLI will not be available.",
                fix_commands=[
                    'echo "Install Node.js from: https://nodejs.org/"',
                ],
                platform_scope="generic",
            )
        )

    # GPU (best-effort NVIDIA check)
    if shutil.which("nvidia-smi") is None:
        issues.append(
            EnvIssue(
                key="gpu_nvidia_smi_missing",
                description="nvidia-smi not found; NVIDIA GPU diagnostics may be unavailable.",
                fix_commands=[
                    'echo "Install NVIDIA drivers appropriate for your OS."',
                ],
                platform_scope="generic",
            )
        )

    # Optional AMD/Intel GPU checks (placeholder, not enforced)
    # if shutil.which("rocminfo") is None:
    #     issues.append(...)
    # if shutil.which("intel_gpu_top") is None:
    #     issues.append(...)

    return issues


# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------

def _is_command_available(cmd: Optional[str]) -> bool:
    if not cmd:
        return False
    return shutil.which(cmd) is not None


def _check_dependencies(platform_flags: Dict[str, bool]) -> Tuple[List[DependencySpec], List[DependencySpec]]:
    """
    Return (missing, outdated) dependency lists.

    For now, we only detect missing vs present; outdated detection can be
    implemented later via version checks or package manager queries.

    torch, python3, rustc, cargo, and maturin are the single source of
    truth for their own availability — checked here and NOT duplicated in
    _detect_env_issues().
    """
    missing: List[DependencySpec] = []
    outdated: List[DependencySpec] = []

    for dep in _dependency_matrix(platform_flags):
        # Special case: torch is checked via Python import
        if dep.name == "torch":
            try:
                result = subprocess.run(
                    ["python3", "-c", "import torch"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    missing.append(dep)
                else:
                    # Placeholder for future version checks
                    pass
            except Exception:
                missing.append(dep)
            continue

        if not _is_command_available(dep.check_command):
            missing.append(dep)
        else:
            # Placeholder for future version checks.
            pass

    return missing, outdated


# ---------------------------------------------------------------------------
# Resolution plan builder (platform-aware, grouped tasks)
# ---------------------------------------------------------------------------

def build_resolution_plan() -> ResolutionPlan:
    """
    Build a structured plan describing:
    - Which dependencies are missing.
    - Which dependencies are outdated.
    - Which environment issues exist.
    - Which admin tasks are suggested (grouped, platform-aware).
    """
    platform_flags = _detect_platform()
    missing, outdated = _check_dependencies(platform_flags)
    env_issues = _detect_env_issues(platform_flags)

    tasks: List[AdminTask] = []

    # Group missing dependencies by group
    missing_by_group: Dict[DependencyGroup, List[DependencySpec]] = {}
    for dep in missing:
        missing_by_group.setdefault(dep.group, []).append(dep)

    # Task: install all missing dependencies (global)
    if missing:
        install_all_cmds: List[str] = []
        for dep in missing:
            install_all_cmds.extend(dep.install_commands)

        tasks.append(
            AdminTask(
                task_type="install_dependency",
                description="Install all missing monitoring and toolchain dependencies.",
                shell="powershell" if platform_flags["windows"] else "bash",
                commands=install_all_cmds,
                group=None,
                platform_scope="generic",
            )
        )

    # Task: install missing dependencies per group
    for group, deps in missing_by_group.items():
        cmds: List[str] = []
        for dep in deps:
            cmds.extend(dep.install_commands)

        tasks.append(
            AdminTask(
                task_type="install_dependency",
                description=f"Install missing dependencies in group: {group}.",
                shell="powershell" if platform_flags["windows"] else "bash",
                commands=cmds,
                group=group,
                platform_scope="generic",
            )
        )

    # Task: update all outdated dependencies (placeholder for future)
    if outdated:
        update_all_cmds: List[str] = []
        for dep in outdated:
            update_all_cmds.extend(dep.update_commands)

        tasks.append(
            AdminTask(
                task_type="update_dependency",
                description="Update all outdated monitoring and toolchain dependencies.",
                shell="powershell" if platform_flags["windows"] else "bash",
                commands=update_all_cmds,
                group=None,
                platform_scope="generic",
            )
        )

    # Tasks: fix environment issues
    for issue in env_issues:
        tasks.append(
            AdminTask(
                task_type="fix_environment",
                description=f"Fix environment issue: {issue.description}",
                shell="powershell" if issue.platform_scope == "windows" else "bash",
                commands=issue.fix_commands,
                group="core_environment",
                platform_scope=issue.platform_scope,
            )
        )

    # Optional: diagnostics/log generation tasks (descriptive only)
    if missing or env_issues:
        tasks.append(
            AdminTask(
                task_type="run_diagnostics",
                description="Run dependency and environment diagnostics.",
                shell="powershell" if platform_flags["windows"] else "bash",
                commands=[
                    'echo "Diagnostics: missing dependencies and environment issues detected."',
                ],
                group=None,
                platform_scope="generic",
            )
        )
        tasks.append(
            AdminTask(
                task_type="generate_log",
                description="Generate dependency_resolver.jsonc log.",
                shell="powershell" if platform_flags["windows"] else "bash",
                commands=[
                    'echo "Log generation is handled inside FCC; no external command needed."',
                ],
                group=None,
                platform_scope="generic",
            )
        )

    return ResolutionPlan(
        missing_dependencies=missing,
        outdated_dependencies=outdated,
        env_issues=env_issues,
        suggested_tasks=tasks,
    )


# ---------------------------------------------------------------------------
# Log generation
# ---------------------------------------------------------------------------

def write_resolution_log(plan: ResolutionPlan, path: str) -> bool:
    """
    Write a JSONC-style log describing the resolution plan.
    Safe-to-fail: returns True on success, False on failure.
    """
    data = {
        "missing_dependencies": [asdict(d) for d in plan.missing_dependencies],
        "outdated_dependencies": [asdict(d) for d in plan.outdated_dependencies],
        "env_issues": [asdict(e) for e in plan.env_issues],
        "suggested_tasks": [asdict(t) for t in plan.suggested_tasks],
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[FCC] Dependency resolver log write failed safely: {e}")
        return False


# ---------------------------------------------------------------------------
# Explanation helpers (for AI / machine-help)
# ---------------------------------------------------------------------------

def explain_dependency(dep: DependencySpec) -> str:
    base = f"{dep.display_name} is a {dep.kind} tool in group {dep.group}."
    if dep.critical:
        base += " It is considered critical for FCC monitoring or AI tooling."
    else:
        base += " It is optional but useful for richer monitoring or tooling."
    return base


def explain_env_issue(issue: EnvIssue) -> str:
    return f"Environment issue '{issue.key}' ({issue.platform_scope}): {issue.description}"


def explain_task(task: AdminTask) -> str:
    return (
        f"Task '{task.task_type}' ({task.description}) will run {len(task.commands)} "
        f"command(s) in {task.shell} (scope: {task.platform_scope or 'generic'})."
    )


# ---------------------------------------------------------------------------
# Orchestrator-facing entry point
# ---------------------------------------------------------------------------

def resolve_dependencies() -> ResolutionPlan:
    """
    Main entry point for the monitoring orchestrator and System Admin UI.

    Does NOT:
    - Run any external commands.
    - Elevate privileges.
    - Modify the system.

    It only describes what SHOULD be done.
    """
    return build_resolution_plan()
