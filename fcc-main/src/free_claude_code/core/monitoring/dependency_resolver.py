from dataclasses import dataclass
from typing import List
"""
Minimal stub for dependency_resolver.

Upstream FCC includes a full dependency analysis system.
Your enhanced FCC tree does not require it, but the orchestrator
attempts to import it. This stub satisfies the import without
changing behavior.
"""


@dataclass
class DependencyIssue:
    name: str
    detail: str

@dataclass
class ResolutionPlan:
    missing_dependencies: List[DependencyIssue]
    outdated_dependencies: List[DependencyIssue]
    env_issues: List[DependencyIssue]
    suggested_tasks: List[DependencyIssue]

def resolve_dependencies():
    """Return an empty resolution plan (safe default)."""
    return ResolutionPlan(
        missing_dependencies=[],
        outdated_dependencies=[],
        env_issues=[],
        suggested_tasks=[],
    )

def write_resolution_log(plan, path):
    """Safe no-op."""
    try:
        with open(path, "w") as f:
            f.write("// dependency resolver stub\n")
    except Exception:
        pass

def explain_dependency(dep):
    return f"Dependency explanation stub for {dep}"

def explain_env_issue(issue):
    return f"Environment issue stub for {issue}"

def explain_task(task):
    return f"Task explanation stub for {task}"
