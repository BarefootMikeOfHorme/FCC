"""Enhanced IDE-like terminal interface for Free Claude Code."""

from __future__ import annotations

import sys
import time
from datetime import datetime

from typing import Dict, List, Optional, Any

import typer
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.text import Text
from rich import box
from rich.align import Align

from free_claude_code.core.version import package_version

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

# Optional orchestrator hook (safe-to-fail)
try:
    from free_claude_code.cli.monitoring_orchestrator import monitoring_ready
except Exception:
    monitoring_ready = None


app = typer.Typer(help="Free Claude Code IDE-like terminal interface")
console = Console()


class MockData:
    """Mock data for demo mode; in live mode this would come from FCC services."""

    def __init__(self) -> None:
        self.agents = {
            "main": {"status": "active", "tasks": 3, "uptime": "2h 15m"},
            "project": {"status": "busy", "tasks": 7, "uptime": "1h 42m"},
            "assistant1": {"status": "idle", "tasks": 0, "uptime": "45m"},
            "assistant2": {"status": "active", "tasks": 2, "uptime": "38m"},
        }
        self.files = [
            {"name": "src/main.py", "size": "2.4 KB", "modified": "2 min ago", "type": "file", "status": "normal"},
            {"name": "src/utils.py", "size": "1.8 KB", "modified": "5 min ago", "type": "file", "status": "warning"},
            {"name": "tmp/error.log", "size": "15.2 KB", "modified": "1 min ago", "type": "file", "status": "compile_error"},
            {"name": "docs/", "size": "--", "modified": "10 min ago", "type": "dir", "status": "normal"},
            {"name": "suspicious.exe", "size": "450 KB", "modified": "30 sec ago", "type": "file", "status": "threat"},
        ]
        self.metrics = {
            "cpu": 45.2,
            "memory": 62.8,
            "message_throughput": 125.5,
            "active_agents": 4,
        }
        self.notifications = [
            {"time": "10:32:15", "message": "Agent 'assistant1' spawned", "type": "info"},
            {"time": "10:31:42", "message": "Memory cleanup completed", "type": "success"},
            {"time": "10:30:18", "message": "Threat detected in sandbox-3", "type": "warning"},
            {"time": "10:29:05", "message": "Project agent started task compilation", "type": "info"},
        ]
        self.errors = [
            {
                "time": "10:31:20",
                "message": "Failed to connect to NVIDIA NIM API",
                "details": "Timeout after 30s",
                "agent": "project",
            },
            {
                "time": "10:28:45",
                "message": "Invalid syntax in src/utils.py:12",
                "details": "Missing closing parenthesis",
                "agent": "assistant1",
            },
        ]


mock_data = MockData()


def make_layout() -> Layout:
    """Create the layout for the IDE terminal interface."""
    layout = Layout(name="root")

    layout.split(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3),
    )

    layout["body"].split_row(
        Layout(name="left_column", ratio=2),
        Layout(name="right_column", size=30),
    )

    layout["left_column"].split_column(
        Layout(name="metrics", size=8),
        Layout(name="notifications", size=8),
        Layout(name="errors", size=8),
        Layout(name="terminal_output", ratio=1),
    )

    layout["right_column"].update(
        Panel(
            create_file_explorer(),
            title="File Explorer",
            border_style="magenta",
            box=box.ROUNDED,
        )
    )

    layout["terminal_output"].split_column(
        Layout(name="output", ratio=3),
        Layout(name="input", size=3),
    )

    layout["header"].update(create_header())
    layout["footer"].update(create_footer())

    layout["metrics"].update(create_metrics_panel())
    layout["notifications"].update(create_notifications_panel())
    layout["errors"].update(create_errors_panel())
    layout["terminal_output"]["output"].update(create_terminal_output())
    layout["terminal_output"]["input"].update(create_input_panel())

    return layout


def create_header() -> Panel:
    """Create the header panel."""
    header_text = Text()
    header_text.append("FREE CLAUDE CODE IDE TERMINAL", style="bold blue")
    header_text.append(" | ")
    header_text.append(f"v{package_version()}", style="dim")
    header_text.append(" | ")
    header_text.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), style="dim")

    return Panel(Align.center(header_text), style="bold blue", box=box.DOUBLE)


def create_agent_tree() -> Tree:
    """Create a tree view of the agent hierarchy."""
    tree = Tree("🖥️  Free Claude Code Agent Hierarchy", guide_style="bold bright_blue")

    main_branch = tree.add("👤 Main Agent (Global Governance)")
    main_branch.add(f"[green]●[/green] Status: {mock_data.agents['main']['status']}")
    main_branch.add(f"[blue]⚡[/blue] Tasks: {mock_data.agents['main']['tasks']}")
    main_branch.add(f"[yellow]⏱️[/yellow] Uptime: {mock_data.agents['main']['uptime']}")

    project_branch = tree.add("📁 Project Agent (Specialization)")
    project_branch.add(f"[yellow]●[/yellow] Status: {mock_data.agents['project']['status']}")
    project_branch.add(f"[blue]⚡[/blue] Tasks: {mock_data.agents['project']['tasks']}")
    project_branch.add(f"[yellow]⏱️[/yellow] Uptime: {mock_data.agents['project']['uptime']}")

    assistant_branch = tree.add("🤖 Assistant Agents (Task Workers)")
    for agent_name, agent_data in mock_data.agents.items():
        if agent_name.startswith("assistant"):
            status_color = "green" if agent_data["status"] == "active" else "dim"
            assistant_branch.add(
                f"[{status_color}]●[/{status_color}] {agent_name.title()}: "
                f"{agent_data['status']} ({agent_data['tasks']} tasks)"
            )

    return tree


def create_file_explorer() -> Table:
    """Create a file explorer table with visual indicators."""
    table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE_HEAD)
    table.add_column("Name", style="cyan", width=25)
    table.add_column("Size", justify="right", style="dim", width=10)
    table.add_column("Modified", style="dim", width=14)
    table.add_column("Type", justify="center", width=8)
    table.add_column("Status", justify="center", width=12)

    for file_info in mock_data.files:
        status = file_info["status"]
        if status == "normal":
            status_display = "[white]◦[/white]"
        elif status == "warning":
            status_display = "[yellow]⚠️[/yellow]"
        elif status == "compile_error":
            status_display = "[red]❌[/red]"
        elif status == "threat":
            status_display = "[purple]🛡️[/purple]"
        else:
            status_display = "[white]◦[/white]"

        if file_info["type"] == "dir":
            type_display = "📁 Dir"
        elif file_info["name"].endswith(".py"):
            type_display = "🐍 Py"
        elif file_info["name"].endswith(".log"):
            type_display = "📄 Log"
        elif file_info["name"].endswith(".exe"):
            type_display = "⚙️ Exe"
        else:
            type_display = "📄 File"

        table.add_row(
            file_info["name"],
            file_info["size"],
            file_info["modified"],
            type_display,
            status_display,
        )

    return table


def create_metrics_panel() -> Panel:
    """Create a metrics panel with simple bar visualization."""
    cpu_percent = mock_data.metrics["cpu"]
    memory_percent = mock_data.metrics["memory"]

    def make_bar(percent: float, width: int = 20) -> str:
        filled = int((percent / 100.0) * width)
        return "█" * filled + "░" * (width - filled)

    cpu_bar = make_bar(cpu_percent)
    memory_bar = make_bar(memory_percent)

    throughput = min(mock_data.metrics["message_throughput"], 200.0)
    throughput_bar_width = 20
    throughput_filled = int((throughput / 200.0) * throughput_bar_width)
    throughput_bar = "█" * throughput_filled + "░" * (throughput_bar_width - throughput_filled)

    metrics_text = Text()
    metrics_text.append("📊 System Metrics\n", style="bold cyan")
    metrics_text.append(f"CPU Usage:       [{cpu_bar}] {cpu_percent:5.1f}%\n")
    metrics_text.append(f"Memory Usage:    [{memory_bar}] {memory_percent:5.1f}%\n")
    metrics_text.append(
        f"Msg Throughput:  [{throughput_bar}] "
        f"{mock_data.metrics['message_throughput']:5.1f} msg/sec\n"
    )
    metrics_text.append(f"Active Agents:   {mock_data.metrics['active_agents']}\n")

    return Panel(metrics_text, title="Metrics", border_style="cyan", box=box.ROUNDED)


def create_notifications_panel() -> Panel:
    """Create a panel showing recent notifications."""
    notifications_text = Text()
    notifications_text.append("🔔 Recent Notifications\n", style="bold yellow")

    for notif in mock_data.notifications[-5:]:
        time_str = notif["time"]
        message = notif["message"]
        notif_type = notif["type"]

        if notif_type == "info":
            style = "cyan"
        elif notif_type == "success":
            style = "green"
        elif notif_type == "warning":
            style = "yellow"
        elif notif_type == "error":
            style = "red"
        else:
            style = "white"

        notifications_text.append(f"[{time_str}] ", style="dim")
        notifications_text.append(f"{message}\n", style=style)

    return Panel(notifications_text, title="Notifications", border_style="yellow", box=box.ROUNDED)


def create_errors_panel() -> Panel:
    """Create a collapsible errors panel."""
    errors_text = Text()
    errors_text.append("⚠️  System Errors\n", style="bold red")

    if not mock_data.errors:
        errors_text.append("No errors reported\n", style="dim green")
    else:
        for error in mock_data.errors[-3:]:
            errors_text.append(f"[{error['time']}] ", style="dim")
            errors_text.append(f"{error['message']}\n", style="red")
            errors_text.append(f"  Details: {error['details']}\n", style="dim red")
            errors_text.append(f"  Agent: {error['agent']}\n", style="dim blue")
            errors_text.append("\n")

    errors_text.append("💡 Press 'e' to toggle error details (future feature)\n", style="bold blue")

    return Panel(errors_text, title="Errors", border_style="red", box=box.ROUNDED)


def create_terminal_output() -> Panel:
    """Create the main terminal output area."""
    output_text = Text()

    output_text.append("Welcome to Free Claude Code IDE Terminal\n", style="bold white")
    output_text.append("📁 Current directory: ", style="dim")
    output_text.append(
        "file:///home/user/free-claude-code-main\n",
        style="underline blue",
    )

    output_text.append("\n🤖 Active Agents: ", style="bold cyan")
    output_text.append("Main(", style="dim")
    output_text.append("active", style="green")
    output_text.append(") | Project(", style="dim")
    output_text.append("busy", style="yellow")
    output_text.append(") | Assistant1(", style="dim")
    output_text.append("idle", style="dim")
    output_text.append(") | Assistant2(", style="dim")
    output_text.append("active", style="green")
    output_text.append(")\n", style="dim")

    output_text.append("\n💡 Try commands: ", style="bold yellow")
    output_text.append("[fcc-health]", style="green bold")
    output_text.append(" | ", style="dim")
    output_text.append("[fcc-setup]", style="green bold")
    output_text.append(" | ", style="dim")
    output_text.append("[help]", style="green bold")
    output_text.append("\n")

    output_text.append("📄 Sample Memory Item (JSONC):\n", style="bold magenta")
    output_text.append("  [JSON syntax highlighting available]\n", style="dim cyan")

    output_text.append("\n📝 Memory Summary (Markdown):\n", style="bold magenta")
    output_text.append("  [Markdown rendering available]\n", style="dim cyan")

    return Panel(output_text, title="Terminal Output", border_style="green", box=box.ROUNDED)


def create_input_panel() -> Panel:
    """Create the input panel with command palette hint."""
    input_text = Text()
    input_text.append("❯ ", style="bold cyan")
    input_text.append("Type commands here. ", style="white")
    input_text.append("[Ctrl+Shift+P] for Command Palette", style="dim yellow")

    return Panel(input_text, title="Command Input", border_style="blue", box=box.ROUNDED)


def create_footer() -> Panel:
    """Create the footer panel."""
    footer_text = Text()
    footer_text.append("💡 Shortcuts: ", style="bold blue")
    footer_text.append("[F1] Help | ", style="dim")
    footer_text.append("[F2] Settings | ", style="dim")
    footer_text.append("[F3] Agent Manager | ", style="dim")
    footer_text.append("[F4] File Explorer | ", style="dim")
    footer_text.append("[F5] Metrics | ", style="dim")
    footer_text.append("[Ctrl+C] Quit", style="dim")

    return Panel(Align.center(footer_text), style="bold blue", box=box.DOUBLE)


def update_layout(layout: Layout) -> None:
    """Update all panels in the layout with fresh data."""
    layout["header"].update(create_header())
    layout["footer"].update(create_footer())

    layout["metrics"].update(create_metrics_panel())
    layout["notifications"].update(create_notifications_panel())
    layout["errors"].update(create_errors_panel())
    layout["terminal_output"]["output"].update(create_terminal_output())
    layout["terminal_output"]["input"].update(create_input_panel())


@app.command()
def launch(
    refresh_rate: float = typer.Option(1.0, "--refresh", "-r", help="Refresh rate in seconds"),
    demo_mode: bool = typer.Option(True, "--demo/--live", help="Run in demo mode with mock data or connect to live FCC"),
) -> None:
    """Launch the Free Claude Code IDE-like terminal interface."""

    if demo_mode:
        console.print("[yellow]Running in DEMO mode with mock data[/yellow]")
        console.print("[dim]To connect to live FCC server, use --live flag[/dim]\n")

    layout = make_layout()

    try:
        with Live(layout, refresh_per_second=4, screen=True):
            while True:
                update_layout(layout)
                time.sleep(refresh_rate)
    except KeyboardInterrupt:
        console.print("\n[yellow]IDE Terminal stopped.[/yellow]")
    except Exception as exc:
        console.print(f"\n[red]Error running IDE terminal: {exc}[/red]")
        if log_with_context:
            try:
                log_with_context(f"IDE terminal error: {exc}", level="error")
            except Exception:
                pass
        if diagnose_system:
            try:
                diagnose_system()
            except Exception:
                pass

    if monitoring_ready:
        try:
            monitoring_ready()
        except Exception:
            pass


@app.command()
def health() -> None:
    """Show health information in IDE terminal format (placeholder)."""
    console.print("[green]Health check would be integrated here[/green]")
    console.print("[dim]This is a placeholder for the IDE terminal health view[/dim]")


if __name__ == "__main__":
    app()
