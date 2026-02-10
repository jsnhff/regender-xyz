"""
Live Display Module

Provides a split-screen live-updating interface with project panel.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

from src.progress import CharacterPreview, ProgressContext, ProgressEvent, Stage, StageCompleteEvent


@dataclass
class ProjectState:
    """Tracks the current project state."""

    book_path: Optional[Path] = None
    book_title: Optional[str] = None
    transform_type: Optional[str] = None
    status: str = "Ready"
    status_icon: str = "⏸"
    output_path: Optional[str] = None
    characters_found: int = 0
    chapters_total: int = 0
    chapters_done: int = 0
    current_stage: Optional[Stage] = None
    stage_progress: float = 0.0
    elapsed_time: float = 0.0
    estimated_remaining: Optional[float] = None
    api_calls: int = 0
    tokens_used: int = 0
    errors: list[str] = field(default_factory=list)


class LiveDisplay:
    """Split-screen live display with project panel."""

    LOGO = """[bold cyan]                               _
  _ __ ___  __ _  ___ _ __   __| | ___ _ __
 | '__/ _ \\/ _` |/ _ \\ '_ \\ / _` |/ _ \\ '__|
 | | |  __/ (_| |  __/ | | | (_| |  __/ |
 |_|  \\___|\\__, |\\___|_| |_|\\__,_|\\___|_|
           |___/                    [dim]xyz[/dim][/bold cyan]"""

    STAGE_NAMES = {
        Stage.PARSING: "Parsing",
        Stage.ANALYZING: "Analyzing",
        Stage.TRANSFORMING: "Transforming",
        Stage.QUALITY_CONTROL: "Quality Check",
    }

    STAGE_ICONS = {
        Stage.PARSING: "📖",
        Stage.ANALYZING: "🔍",
        Stage.TRANSFORMING: "✨",
        Stage.QUALITY_CONTROL: "✓",
    }

    def __init__(self):
        """Initialize the display."""
        self.console = Console()
        self.state = ProjectState()
        self.live: Optional[Live] = None
        self.start_time: Optional[float] = None
        self._progress: Optional[Progress] = None
        self._task_id: Optional[int] = None

    def create_progress_context(self) -> ProgressContext:
        """Create a progress context for reporting."""
        return ProgressContext(
            on_progress=self._on_progress,
            on_stage_complete=self._on_stage_complete,
        )

    def _on_progress(self, event: ProgressEvent) -> None:
        """Handle progress updates."""
        self.state.current_stage = event.stage
        self.state.stage_progress = event.current / event.total if event.total > 0 else 0

        if event.stage == Stage.TRANSFORMING:
            self.state.chapters_done = event.current
            self.state.chapters_total = event.total

        # Update status
        stage_name = self.STAGE_NAMES.get(event.stage, event.stage.value)
        icon = self.STAGE_ICONS.get(event.stage, "⏳")
        self.state.status = f"{stage_name}... ({event.current}/{event.total})"
        self.state.status_icon = icon

        # Estimate remaining time
        if self.start_time and event.current > 0:
            elapsed = time.time() - self.start_time
            rate = event.current / elapsed
            remaining = (event.total - event.current) / rate if rate > 0 else None
            self.state.estimated_remaining = remaining
            self.state.elapsed_time = elapsed

        self._refresh()

    def _on_stage_complete(self, event: StageCompleteEvent) -> None:
        """Handle stage completion."""
        stage_name = self.STAGE_NAMES.get(event.stage, event.stage.value)
        self.state.status = f"{stage_name} complete"
        self.state.status_icon = "✓"
        self.state.stage_progress = 1.0

        if event.stage == Stage.ANALYZING:
            self.state.characters_found = event.stats.get("total_characters", 0)

        self._refresh()

    def _refresh(self) -> None:
        """Refresh the live display."""
        if self.live:
            self.live.refresh()

    def _make_layout(self, main_content: str = "") -> Layout:
        """Create the split-screen layout."""
        layout = Layout()

        layout.split_row(
            Layout(name="main", ratio=2),
            Layout(name="sidebar", ratio=1, minimum_size=30),
        )

        # Main content
        main_panel = Panel(
            Text.from_markup(main_content) if main_content else Text(""),
            border_style="dim",
            title="[bold]regender[/bold]",
            title_align="left",
        )
        layout["main"].update(main_panel)

        # Sidebar with project info
        layout["sidebar"].update(self._make_project_panel())

        return layout

    def _make_project_panel(self) -> Panel:
        """Create the project info panel."""
        sections = []

        # Book section
        sections.append(
            self._make_section("Book", self.state.book_title or "[dim]Not selected[/dim]", "📚")
        )

        # Transform section
        sections.append(
            self._make_section(
                "Transform", self.state.transform_type or "[dim]Not selected[/dim]", "🔄"
            )
        )

        # Status section with progress
        status_content = self._make_status_content()
        sections.append(status_content)

        # Stats section (if processing)
        if self.state.current_stage:
            sections.append(self._make_stats_section())

        # Output section
        if self.state.output_path:
            sections.append(
                self._make_section(
                    "Output", f"[green]{Path(self.state.output_path).name}[/green]", "📄"
                )
            )

        content = Group(*sections)

        return Panel(
            content,
            title="[bold]PROJECT[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )

    def _make_section(self, title: str, value: str, icon: str = "") -> Text:
        """Create a section for the project panel."""
        text = Text()
        text.append(f"{icon} " if icon else "")
        text.append(f"{title}\n", style="bold dim")
        text.append(f"  {value}\n\n")
        return text

    def _make_status_content(self) -> Text:
        """Create the status section content."""
        text = Text()
        text.append(f"{self.state.status_icon} Status\n", style="bold dim")
        text.append(f"  {self.state.status}\n")

        # Progress bar
        if self.state.current_stage and self.state.stage_progress < 1.0:
            bar_width = 20
            filled = int(bar_width * self.state.stage_progress)
            empty = bar_width - filled
            bar = "█" * filled + "░" * empty
            percent = int(self.state.stage_progress * 100)
            text.append(f"  [cyan]{bar}[/cyan] {percent}%\n")

        # Time estimates
        if self.state.elapsed_time > 0:
            elapsed_str = self._format_time(self.state.elapsed_time)
            text.append(f"  [dim]Elapsed: {elapsed_str}[/dim]\n")

        if self.state.estimated_remaining is not None and self.state.estimated_remaining > 0:
            remaining_str = self._format_time(self.state.estimated_remaining)
            text.append(f"  [dim]Remaining: ~{remaining_str}[/dim]\n")

        text.append("\n")
        return text

    def _make_stats_section(self) -> Text:
        """Create the stats section."""
        text = Text()
        text.append("📊 Stats\n", style="bold dim")

        if self.state.characters_found > 0:
            text.append(f"  Characters: {self.state.characters_found}\n")

        if self.state.chapters_total > 0:
            text.append(f"  Chapters: {self.state.chapters_done}/{self.state.chapters_total}\n")

        if self.state.api_calls > 0:
            text.append(f"  API calls: {self.state.api_calls}\n")

        if self.state.tokens_used > 0:
            text.append(f"  Tokens: {self.state.tokens_used:,}\n")

        text.append("\n")
        return text

    def _format_time(self, seconds: float) -> str:
        """Format seconds into human-readable time."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"

    def set_book(self, path: Path, title: Optional[str] = None) -> None:
        """Set the current book."""
        self.state.book_path = path
        self.state.book_title = title or path.stem
        self.state.status = "Book selected"
        self.state.status_icon = "📚"

    def set_transform(self, transform_type: str) -> None:
        """Set the transformation type."""
        self.state.transform_type = transform_type
        self.state.status = "Ready to transform"
        self.state.status_icon = "▶"

    def set_processing(self) -> None:
        """Mark as processing."""
        self.state.status = "Starting..."
        self.state.status_icon = "⏳"
        self.start_time = time.time()

    def set_complete(self, output_path: str, stats: dict[str, Any]) -> None:
        """Mark as complete."""
        self.state.status = "Complete!"
        self.state.status_icon = "✅"
        self.state.output_path = output_path
        self.state.api_calls = stats.get("api_calls", 0)
        self.state.tokens_used = stats.get("total_tokens", 0)
        self.state.stage_progress = 1.0

        if self.start_time:
            self.state.elapsed_time = time.time() - self.start_time
        self.state.estimated_remaining = None

    def set_error(self, message: str) -> None:
        """Set error state."""
        self.state.status = f"Error: {message}"
        self.state.status_icon = "❌"
        self.state.errors.append(message)

    def print_with_panel(self, content: str) -> None:
        """Print content with the project panel visible."""
        layout = self._make_layout(content)
        self.console.print(layout)

    def start_live(self, content: str = "") -> None:
        """Start live updating display."""
        layout = self._make_layout(content)
        self.live = Live(layout, console=self.console, refresh_per_second=4)
        self.live.start()

    def update_main(self, content: str) -> None:
        """Update the main content area."""
        if self.live:
            layout = self._make_layout(content)
            self.live.update(layout)

    def stop_live(self) -> None:
        """Stop live updating display."""
        if self.live:
            self.live.stop()
            self.live = None

    def show_summary(self) -> None:
        """Show final summary."""
        self.console.print()

        if self.state.output_path:
            self.console.print("[green]✓ Transformation complete![/green]")
            self.console.print()

            # Stats line
            parts = []
            if self.state.elapsed_time > 0:
                parts.append(f"Time: {self._format_time(self.state.elapsed_time)}")
            if self.state.api_calls > 0:
                parts.append(f"API calls: {self.state.api_calls}")
            if self.state.tokens_used > 0:
                parts.append(f"Tokens: {self.state.tokens_used:,}")

            if parts:
                self.console.print(f"  {' | '.join(parts)}")
                self.console.print()

            self.console.print(f"  Output: [cyan]{self.state.output_path}[/cyan]")
        else:
            self.console.print("[red]✗ Transformation failed[/red]")
            for error in self.state.errors:
                self.console.print(f"  {error}")

        self.console.print()
