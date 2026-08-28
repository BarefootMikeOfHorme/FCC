"""Health reporting command for Free Claude Code."""

from __future__ import annotations

import sys
import time
from typing import Sequence, Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from free_claude_code.core.version import package_version

# Optional orchestrator hook (safe-to-fail)
try:
    from free_claude_code.cli.monitoring_orchestrator import monitoring_ready
except Exception:
    monitoring_ready = None

# Optional diagnostics hook (safe-to-fail)
try:
    from free_claude_code.core.system_diagnostics import diagnose_system
except Exception:
    diagnose_system = None

# Optional logging hook (safe-to-fail)
try:
    from free_claude_code.core.logging_integration import log_with_context
except Exception:
    log_with_context = None


app = typer.Typer(help="Free Claude Code health reporting")
console = Console()


def _get_health_data() -> dict:
    """Fetch health data from the FCC server with safe-to-fail diagnostics."""
    try:
        response = httpx.get("http://127.0.0.1:8082/health", timeout=5.0)
        if response.status_code == 200:
            return response.json()
        return {
            "status": "error",
            "message": f"Server returned status {response.status_code}",
        }
    except httpx.ConnectError as exc:
        if log_with_context:
            try:
                log_with_context("Health check: cannot connect to FCC server", level="error")
            except Exception:
                pass
        return {"status": "error", "message": "Cannot connect to FCC server. Is it running?"}
    except Exception as exc:
        if log_with_context:
            try:
                log_with_context(f"Health check unexpected error: {exc}", level="error")
            except Exception:
                pass
        return {"status": "error", "message": f"Unexpected error: {str(exc)}"}


def _display_health_basic(health_data: dict):
    """Display basic health information."""
    status = health_data.get("status", "unknown")

    if status == "healthy":
        status_text = "[green]PASS[/green]"
        border_style = "green"
    else:
        status_text = f"[red]FAIL[/red] ({status})"
        border_style = "red"

    console.print(
        Panel.fit(
            f"Free Claude Code Health Status\n\n{status_text}",
            border_style=border_style,
            title="System Health",
        )
    )


def _display_health_detailed(health_data: dict):
    """Display detailed health information with structured tables."""

    # System information
    system_info = health_data.get("system", {})
    if system_info:
        system_table = Table(title="System Information", box=box.SIMPLE)
        system_table.add_column("Property", style="cyan")
        system_table.add_column("Value", style="white")

        system_table.add_row("Platform", system_info.get("platform", "Unknown"))
        system_table.add_row("Python Version", system_info.get("python_version", "Unknown"))
        system_table.add_row("Uptime", f"{system_info.get('uptime_seconds', 0):.0f} seconds")
        system_table.add_row("Boot Time", str(system_info.get("boot_time", "Unknown")))

        console.print(system_table)

    # Resource usage
    resources = health_data.get("resources", {})
    if resources:
        resources_table = Table(title="Resource Usage", box=box.SIMPLE)
        resources_table.add_column("Resource", style="cyan")
        resources_table.add_column("Usage", style="white")

        memory = resources.get("memory", {})
        if memory:
            resources_table.add_row(
                "Memory Usage",
                f"{memory.get('percent_used', 0):.1f}% "
                f"({memory.get('used', 0) // (1024**2)} MB / "
                f"{memory.get('total', 0) // (1024**2)} MB)"
            )

        cpu = resources.get("cpu", {})
        if cpu:
            resources_table.add_row(
                "CPU Usage",
                f"{cpu.get('usage_percent', 0):.1f}% ({cpu.get('count', 0)} cores)"
            )

        console.print(resources_table)

    # Component status
    components = health_data.get("components", {})
    if components:
        components_table = Table(title="Component Status", box=box.SIMPLE)
        components_table.add_column("Component", style="cyan")
        components_table.add_column("Status", style="white")

        for component, status in components.items():
            if isinstance(status, str) and "error" in status.lower():
                status_display = f"[red]FAIL {status}[/red]"
            elif status == "operational" or status is True:
                status_display = "[green]PASS operational[/green]"
            else:
                status_display = f"[yellow]? {status}[/yellow]"

            components_table.add_row(component.replace("_", " ").title(), status_display)

        console.print(components_table)


@app.command()
def check(
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed health information"),
    refresh: float = typer.Option(0.0, "--refresh", "-r", help="Auto-refresh interval in seconds (0 for one-time)"),
):
    """Check Free Claude Code system health and status."""

    if refresh > 0:
        console.print(
            f"[cyan]Starting health monitoring with {refresh}s refresh interval. "
            f"Press Ctrl+C to stop.[/cyan]\n"
        )

        try:
            while True:
                console.clear()
                console.print(
                    f"[bold]Free Claude Code Health Monitor[/bold] - "
                    f"{typer.style(str(int(time.time())), dim=True)}"
                )
                console.print("=" * 50)

                health_data = _get_health_data()
                if detailed:
                    _display_health_detailed(health_data)
                else:
                    _display_health_basic(health_data)

                time.sleep(refresh)
        except KeyboardInterrupt:
            console.print("\n[yellow]Health monitoring stopped.[/yellow]")
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Checking system health...", total=None)
            health_data = _get_health_data()

        if detailed:
            _display_health_detailed(health_data)
        else:
            _display_health_basic(health_data)

    # Optional orchestrator readiness signal
    if monitoring_ready:
        try:
            monitoring_ready()
        except Exception:
            pass


if __name__ == "__main__":
    app()
