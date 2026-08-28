"""Rich terminal output formatter for Free Claude Code.

This module provides rich-formatted output capabilities including:
- Progress bars for long-running operations
- Colored output for different verbosity levels
- Structured display panels
- Live updating displays
- Integration with output schemas
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich import box

from .output_schemas import (
    VerbosityLevel,
    OutputFormat,
    QueryResponse,
    LogEntry,
    SecurityAuditLogEntry,
    SystemMetrics,
    ProgressUpdate,
    format_query_response,
    format_log_entry,
)

# Optional FCC integrations
try:
    from .logging_integration import log_with_context
except Exception:
    def log_with_context(message: str, level: str = "info", **ctx: object) -> None:
        return

try:
    from .trace import trace_event
except Exception:
    def trace_event(event: str, **fields: object) -> None:
        return


class RichOutputFormatter:
    """Rich terminal output formatter for FCC.

    This formatter wraps Rich primitives and FCC output schemas to provide:
    - Verbosity-aware rendering
    - Safe-to-fail terminal output
    - Structured panels and tables
    - Progress and status visualization
    """

    def __init__(self, verbosity: VerbosityLevel = VerbosityLevel.NORMAL):
        self.verbosity = verbosity
        self.console = Console()
        self._progress: Optional[Progress] = None
        self._live_display: Optional[Live] = None

        trace_event("rich_formatter.init", verbosity=str(self.verbosity))

    # ------------------------------------------------------------------
    # Query response formatting
    # ------------------------------------------------------------------

    def format_query_response(
        self,
        response: QueryResponse,
        fmt: OutputFormat = OutputFormat.TEXT,
    ) -> Union[str, Panel]:
        trace_event(
            "rich_formatter.format_query_response",
            fmt=str(fmt),
            verbosity=str(self.verbosity),
        )

        if fmt == OutputFormat.JSON:
            return response.model_dump_json(
                indent=2 if self.verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG) else None
            )

        elif fmt == OutputFormat.MARKDOWN:
            md_content = format_query_response(response, self.verbosity, OutputFormat.MARKDOWN)
            return Panel(
                md_content,
                title="[bold blue]Claude Response[/bold blue]",
                border_style="blue",
                padding=(1, 2),
            )

        else:  # TEXT
            if self.verbosity == VerbosityLevel.QUIET:
                return response.response

            elif self.verbosity == VerbosityLevel.NORMAL:
                text = Text(response.response)
                if response.latency_ms:
                    text.append(f"\n[{response.latency_ms:.0f}ms]", style="dim")
                return Panel(text, border_style="dim")

            else:  # VERBOSE, DEBUG, TRACE
                content = Text(response.response)

                metadata_lines = [
                    "",
                    f"[bold]Model:[/bold] {response.model_used}",
                    f"[bold]Time:[/bold] {response.timestamp}",
                ]

                if response.request_id:
                    metadata_lines.append(f"[bold]Request ID:[/bold] {response.request_id}")
                if response.session_id:
                    metadata_lines.append(f"[bold]Session ID:[/bold] {response.session_id}")

                if self.verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG):
                    metadata_lines.extend(
                        [
                            "",
                            "[bold]Token Usage:[/bold]",
                            f"  Prompt: {response.prompt_tokens or 0}",
                            f"  Completion: {response.completion_tokens or 0}",
                            f"  Total: {response.total_tokens or 0}",
                            "",
                            "[bold]Performance:[/bold]",
                            f"  Latency: {response.latency_ms or 0:.1f}ms",
                            f"  Time to First Token: {response.time_to_first_token or 0:.1f}ms",
                            "",
                            "[bold]Quality Scores:[/bold]",
                            f"  Safety: {response.safety_score or 0:.2f}",
                            f"  Relevance: {response.relevance_score or 0:.2f}",
                        ]
                    )

                    if response.metadata:
                        metadata_lines.extend(["", "[bold]Additional Metadata:[/bold]"])
                        for key, value in response.metadata.items():
                            metadata_lines.append(f"  {key}: {value}")

                content.append("\n".join(metadata_lines))

                return Panel(
                    content,
                    title="[bold blue]Claude Response[/bold blue]",
                    border_style="blue",
                    padding=(1, 2),
                )

    # ------------------------------------------------------------------
    # Log entry formatting
    # ------------------------------------------------------------------

    def format_log_entry(
        self,
        entry: LogEntry,
        fmt: OutputFormat = OutputFormat.TEXT,
    ) -> Union[str, Panel, Table, Text]:
        trace_event(
            "rich_formatter.format_log_entry",
            fmt=str(fmt),
            verbosity=str(self.verbosity),
            level=entry.level,
        )

        if fmt == OutputFormat.JSON:
            return entry.model_dump_json(
                indent=2 if self.verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG) else None
            )

        elif fmt == OutputFormat.MARKDOWN:
            md_content = format_log_entry(entry, self.verbosity, OutputFormat.MARKDOWN)
            return Panel(md_content, title="[bold]Log Entry[/bold]", border_style="dim")

        else:  # TEXT
            if self.verbosity == VerbosityLevel.QUIET:
                if entry.level in ("ERROR", "CRITICAL"):
                    level_style = "red" if entry.level == "ERROR" else "bold red"
                    return Text(f"{entry.level}: {entry.message}", style=level_style)
                return ""

            elif self.verbosity == VerbosityLevel.NORMAL:
                level_styles = {
                    "DEBUG": "dim",
                    "INFO": "white",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold red",
                    "SECURITY": "magenta",
                }
                style = level_styles.get(entry.level, "white")
                return Text(f"{entry.level}: {entry.message}", style=style)

            else:  # VERBOSE, DEBUG, TRACE
                table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
                table.add_column("Field", style="dim", width=12)
                table.add_column("Value")

                table.add_row("Timestamp", entry.timestamp)
                table.add_row("Level", self._format_log_level(entry.level))
                table.add_row("Message", entry.message)
                table.add_row("Source", f"{entry.module}:{entry.function}:{entry.line}")

                context_added = False
                if entry.request_id or entry.session_id:
                    table.add_row("", "")
                    context_added = True
                    if entry.request_id:
                        table.add_row("Request ID", entry.request_id)
                    if entry.session_id:
                        table.add_row("Session ID", entry.session_id)

                if isinstance(entry, SecurityAuditLogEntry):
                    if not context_added:
                        table.add_row("", "")
                    table.add_row("Security Level", entry.security_level)
                    table.add_row("Event Type", entry.event_type)
                    if entry.action_taken:
                        table.add_row("Action Taken", entry.action_taken)
                    if entry.outcome:
                        table.add_row("Outcome", entry.outcome)
                    if entry.source_ip:
                        table.add_row("Source IP", entry.source_ip)

                if self.verbosity in (VerbosityLevel.VERBOSE, VerbosityLevel.DEBUG) and entry.metadata:
                    table.add_row("", "")
                    for key, value in entry.metadata.items():
                        table.add_row(f"Metadata.{key}", str(value))

                return Panel(
                    table,
                    title="[bold]Log Entry[/bold]",
                    border_style=self._get_log_level_color(entry.level),
                    padding=(0, 1),
                )

    def _format_log_level(self, level: str) -> Text:
        level_colors = {
            "DEBUG": "dim white",
            "INFO": "white",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold red",
            "SECURITY": "magenta",
        }
        return Text(level, style=level_colors.get(level, "white"))

    def _get_log_level_color(self, level: str) -> str:
        level_colors = {
            "DEBUG": "dim",
            "INFO": "blue",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold red",
            "SECURITY": "magenta",
        }
        return level_colors.get(level, "blue")

    # ------------------------------------------------------------------
    # Progress bar creation and lifecycle
    # ------------------------------------------------------------------

    def create_progress_bar(
        self,
        description: str = "Processing...",
        total: Optional[int] = None,
    ) -> Progress:
        trace_event(
            "rich_formatter.create_progress_bar",
            description=description,
            total=total,
        )

        progress_columns = [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ]

        if total is not None:
            progress_columns.append(
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%")
            )

        progress_columns.extend(
            [
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            ]
        )

        self._progress = Progress(*progress_columns, console=self.console)
        return self._progress

    def start_progress(
        self,
        description: str = "Processing...",
        total: Optional[int] = None,
    ) -> int:
        trace_event(
            "rich_formatter.start_progress",
            description=description,
            total=total,
        )

        if self._progress is None:
            self.create_progress_bar(description, total)

        task_id = self._progress.add_task(description, total=total)
        self._progress.start()
        return task_id

    def update_progress(
        self,
        task_id: int,
        advance: int = 1,
        description: Optional[str] = None,
    ):
        trace_event(
            "rich_formatter.update_progress",
            task_id=task_id,
            advance=advance,
            description=description,
        )

        if self._progress:
            self._progress.update(task_id, advance=advance, description=description)

    def stop_progress(self):
        trace_event("rich_formatter.stop_progress")

        if self._progress:
            self._progress.stop()
            self._progress = None

    # ------------------------------------------------------------------
    # Live display creation and lifecycle
    # ------------------------------------------------------------------

    def create_live_display(self) -> Live:
        trace_event("rich_formatter.create_live_display")

        self._live_display = Live(console=self.console, refresh_per_second=4)
        return self._live_display

    def start_live_display(self):
        trace_event("rich_formatter.start_live_display")

        if self._live_display:
            self._live_display.start()

    def stop_live_display(self):
        trace_event("rich_formatter.stop_live_display")

        if self._live_display:
            self._live_display.stop()
            self._live_display = None

    def update_live_display(self, content: Union[str, Panel, Table]):
        trace_event("rich_formatter.update_live_display")

        if self._live_display:
            self._live_display.update(content)

# ------------------------------------------------------------------
# Global formatter instance
# ------------------------------------------------------------------

_global_formatter: Optional[RichOutputFormatter] = None

def get_rich_formatter(
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
) -> RichOutputFormatter:
    """Return a global RichOutputFormatter instance."""
    global _global_formatter
    if (
        _global_formatter is None
        or _global_formatter.verbosity != verbosity
    ):
        _global_formatter = RichOutputFormatter(verbosity)
    return _global_formatter

# ------------------------------------------------------------------
# Convenience wrappers used by CLI and logging_integration
# ------------------------------------------------------------------

def format_and_print_query(
    response: QueryResponse,
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
    fmt: OutputFormat = OutputFormat.TEXT,
) -> None:
    formatter = get_rich_formatter(verbosity)
    formatted = formatter.format_query_response(response, fmt)
    formatter.console.print(formatted)

def format_and_print_log(
    entry: LogEntry,
    verbosity: VerbosityLevel = VerbosityLevel.NORMAL,
    fmt: OutputFormat = OutputFormat.TEXT,
) -> None:
    formatter = get_rich_formatter(verbosity)
    formatted = formatter.format_log_entry(entry, fmt)

    if isinstance(formatted, (str, Text)):
        if formatted:
            formatter.console.print(formatted)
    else:
        formatter.console.print(formatted)
