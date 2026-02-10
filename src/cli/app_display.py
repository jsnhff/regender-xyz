"""
Unified App Display

A single display class that maintains the split-screen layout throughout
the entire transformation process.
"""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from rich.console import Console, Group, RenderableType
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
)
from rich.table import Table
from rich.text import Text

from src.progress import ProgressContext, ProgressEvent, Stage, StageCompleteEvent

LOGO = """[bold cyan]                               _
  _ __ ___  __ _  ___ _ __   __| | ___ _ __
 | '__/ _ \\/ _` |/ _ \\ '_ \\ / _` |/ _ \\ '__|
 | | |  __/ (_| |  __/ | | | (_| |  __/ |
 |_|  \\___|\\__, |\\___|_| |_|\\__,_|\\___|_|
           |___/                    [dim]xyz[/dim][/bold cyan]"""


@dataclass
class AppState:
    """Application state for display."""

    book_title: Optional[str] = None
    transform_type: Optional[str] = None
    status: str = "Ready"
    status_icon: str = "⏸"
    current_stage: Optional[Stage] = None
    progress: float = 0.0
    progress_current: int = 0
    progress_total: int = 0
    elapsed: float = 0.0
    remaining: Optional[float] = None
    characters: int = 0
    chapters_done: int = 0
    chapters_total: int = 0
    output_path: Optional[str] = None
    complete: bool = False
    error: Optional[str] = None
    # Completed stages with their stats
    completed_stages: list[tuple[Stage, float, dict]] = field(default_factory=list)


class AppDisplay:
    """
    Unified display that maintains split-screen layout throughout processing.
    """

    STAGE_INFO = {
        Stage.PARSING: ("📖", "Parsing"),
        Stage.ANALYZING: ("🔍", "Analyzing"),
        Stage.TRANSFORMING: ("✨", "Transforming"),
        Stage.QUALITY_CONTROL: ("✓", "Quality Check"),
    }

    def __init__(self):
        self.console = Console()
        self.state = AppState()
        self.live: Optional[Live] = None
        self.start_time: Optional[float] = None
        self.main_content: list[str] = []

    def clear(self) -> None:
        """Clear the screen."""
        os.system("cls" if os.name == "nt" else "clear")

    def create_progress_context(self) -> ProgressContext:
        """Create progress context for reporting."""
        return ProgressContext(
            on_progress=self._on_progress,
            on_stage_complete=self._on_stage_complete,
        )

    def _on_progress(self, event: ProgressEvent) -> None:
        """Handle progress updates."""
        self.state.current_stage = event.stage
        self.state.progress_current = event.current
        self.state.progress_total = event.total
        self.state.progress = event.current / event.total if event.total > 0 else 0

        icon, name = self.STAGE_INFO.get(event.stage, ("⏳", event.stage.value))
        self.state.status = f"{name}..."
        self.state.status_icon = icon

        if event.stage == Stage.TRANSFORMING:
            self.state.chapters_done = event.current
            self.state.chapters_total = event.total

        # Estimate remaining time
        if self.start_time and event.current > 0:
            elapsed = time.time() - self.start_time
            self.state.elapsed = elapsed
            rate = event.current / elapsed
            if rate > 0:
                self.state.remaining = (event.total - event.current) / rate

        self._refresh()

    def _on_stage_complete(self, event: StageCompleteEvent) -> None:
        """Handle stage completion."""
        icon, name = self.STAGE_INFO.get(event.stage, ("✓", event.stage.value))

        # Record completed stage
        self.state.completed_stages.append((event.stage, event.elapsed_seconds, event.stats))

        if event.stage == Stage.ANALYZING:
            self.state.characters = event.stats.get("total_characters", 0)
        elif event.stage == Stage.PARSING:
            self.state.chapters_total = event.stats.get("chapters", 0)

        self.state.status = f"{name} complete"
        self.state.status_icon = "✓"
        self.state.progress = 1.0

        self._refresh()

    def _refresh(self) -> None:
        """Refresh the live display."""
        if self.live:
            self.live.update(self._make_layout())

    def _make_layout(self) -> Table:
        """Create the split-screen layout."""
        # Use a grid table to create side-by-side layout
        grid = Table.grid(expand=True)
        grid.add_column("main", ratio=2)
        grid.add_column("panel", width=34)

        # Main content area
        main = self._make_main_content()

        # Project panel
        panel = self._make_project_panel()

        grid.add_row(main, panel)
        return grid

    def _make_main_content(self) -> RenderableType:
        """Create the main content area."""
        parts = [Text.from_markup(LOGO), Text()]

        # Add any queued content
        for line in self.main_content:
            parts.append(Text.from_markup(line))

        # Show completed stages
        for stage, elapsed, stats in self.state.completed_stages:
            icon, name = self.STAGE_INFO.get(stage, ("✓", stage.value))
            stats_str = ", ".join(f"{k}: {v}" for k, v in stats.items())
            line = f"[green]✓[/green] {name} ({elapsed:.1f}s)"
            if stats_str:
                line += f" - {stats_str}"
            parts.append(Text.from_markup(line))

        # Show current progress
        if self.state.current_stage and self.state.progress < 1.0:
            icon, name = self.STAGE_INFO.get(self.state.current_stage, ("⏳", "Processing"))
            pct = int(self.state.progress * 100)

            # Create progress bar
            bar_width = 30
            filled = int(bar_width * self.state.progress)
            empty = bar_width - filled
            bar = "━" * filled + "[dim]━[/dim]" * empty

            progress_line = f"{icon} {name}... [cyan]{bar}[/cyan] {pct}%"
            parts.append(Text.from_markup(progress_line))

        # Show completion
        if self.state.complete:
            parts.append(Text())
            parts.append(Text.from_markup("[bold green]✓ Complete![/bold green]"))
            if self.state.output_path:
                parts.append(Text.from_markup(f"\n  Output: [cyan]{self.state.output_path}[/cyan]"))

        # Show error
        if self.state.error:
            parts.append(Text())
            parts.append(Text.from_markup(f"[bold red]✗ Error:[/bold red] {self.state.error}"))

        return Group(*parts)

    def _make_project_panel(self) -> Panel:
        """Create the project info panel."""
        sections = []

        # Book
        book_text = Text()
        book_text.append("📚 Book\n", style="bold cyan")
        if self.state.book_title:
            title = self.state.book_title[:26] + "..." if len(self.state.book_title) > 29 else self.state.book_title
            book_text.append(f"   {title}\n\n")
        else:
            book_text.append("   [dim]Not selected[/dim]\n\n")
        sections.append(book_text)

        # Transform
        transform_text = Text()
        transform_text.append("🔄 Transform\n", style="bold cyan")
        if self.state.transform_type:
            transform_text.append(f"   {self.state.transform_type}\n\n")
        else:
            transform_text.append("   [dim]Not selected[/dim]\n\n")
        sections.append(transform_text)

        # Status
        status_text = Text()
        status_text.append(f"{self.state.status_icon} Status\n", style="bold cyan")
        status_text.append(f"   {self.state.status}\n")

        # Progress bar in panel
        if self.state.current_stage and 0 < self.state.progress < 1:
            bar_width = 20
            filled = int(bar_width * self.state.progress)
            empty = bar_width - filled
            bar = "█" * filled + "░" * empty
            pct = int(self.state.progress * 100)
            status_text.append(f"   [green]{bar}[/green] {pct}%\n")

        # Time info
        if self.state.elapsed > 0:
            status_text.append(f"   [dim]⏱ {self._fmt_time(self.state.elapsed)}[/dim]")
            if self.state.remaining and self.state.remaining > 1:
                status_text.append(f"[dim] • ~{self._fmt_time(self.state.remaining)} left[/dim]")
            status_text.append("\n")

        status_text.append("\n")
        sections.append(status_text)

        # Stats
        if self.state.characters or self.state.chapters_total:
            stats_text = Text()
            stats_text.append("📊 Stats\n", style="bold cyan")
            if self.state.characters:
                stats_text.append(f"   Characters: {self.state.characters}\n")
            if self.state.chapters_total:
                stats_text.append(f"   Chapters: {self.state.chapters_done}/{self.state.chapters_total}\n")
            stats_text.append("\n")
            sections.append(stats_text)

        # Output
        if self.state.output_path:
            out_text = Text()
            out_text.append("📄 Output\n", style="bold cyan")
            out_name = Path(self.state.output_path).name
            out_text.append(f"   [green]{out_name}[/green]\n")
            sections.append(out_text)

        return Panel(
            Group(*sections),
            title="[bold]PROJECT[/bold]",
            border_style="cyan",
            width=32,
        )

    def _fmt_time(self, secs: float) -> str:
        """Format seconds to human readable."""
        if secs < 60:
            return f"{int(secs)}s"
        elif secs < 3600:
            return f"{int(secs // 60)}m {int(secs % 60)}s"
        else:
            return f"{int(secs // 3600)}h {int((secs % 3600) // 60)}m"

    # Public API

    def set_book(self, title: str) -> None:
        """Set the book title."""
        self.state.book_title = title
        self.state.status = "Book selected"
        self.state.status_icon = "📚"

    def set_transform(self, transform_type: str) -> None:
        """Set the transform type."""
        self.state.transform_type = transform_type
        self.state.status = "Ready"
        self.state.status_icon = "▶"

    def start_processing(self) -> None:
        """Start processing mode."""
        self.start_time = time.time()
        self.state.status = "Starting..."
        self.state.status_icon = "⏳"

    def set_complete(self, output_path: str) -> None:
        """Mark as complete."""
        self.state.complete = True
        self.state.output_path = output_path
        self.state.status = "Complete!"
        self.state.status_icon = "✅"
        self.state.progress = 1.0
        if self.start_time:
            self.state.elapsed = time.time() - self.start_time
        self.state.remaining = None

    def set_error(self, message: str) -> None:
        """Set error state."""
        self.state.error = message
        self.state.status = "Error"
        self.state.status_icon = "❌"

    def add_content(self, content: str) -> None:
        """Add content to main area."""
        self.main_content.append(content)

    def show_static(self, content: str = "") -> None:
        """Show static layout (not live updating)."""
        if content:
            self.main_content.append(content)
        self.console.print(self._make_layout())

    def start_live(self) -> None:
        """Start live updating display."""
        self.live = Live(
            self._make_layout(),
            console=self.console,
            refresh_per_second=4,
            transient=False,
        )
        self.live.start()

    def stop_live(self) -> None:
        """Stop live updating."""
        if self.live:
            self.live.stop()
            self.live = None

    def show_final(self) -> None:
        """Show final state after processing."""
        self.stop_live()
        self.console.print(self._make_layout())
