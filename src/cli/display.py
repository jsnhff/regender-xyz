"""
CLI Display Classes

Rich-based display classes for progress reporting.
"""

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
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

from src.progress import CharacterPreview, ProgressContext, ProgressEvent, Stage, StageCompleteEvent


class BaseDisplay(ABC):
    """Abstract base class for display implementations."""

    @abstractmethod
    def create_progress_context(self) -> ProgressContext:
        """Create a progress context for reporting."""
        ...

    @abstractmethod
    def show_header(self, book_name: str) -> None:
        """Display the header."""
        ...

    @abstractmethod
    def show_summary(
        self,
        elapsed_seconds: float,
        api_calls: int,
        tokens: int,
        output_path: str,
    ) -> None:
        """Display the final summary."""
        ...

    @abstractmethod
    def show_error(self, message: str) -> None:
        """Display an error message."""
        ...


class CLIDisplay(BaseDisplay):
    """Rich-based CLI display with progress bars and character previews."""

    MAX_CHARACTER_PREVIEW = 4

    def __init__(self, console: Optional[Console] = None):
        """Initialize the display."""
        self.console = console or Console()
        self._progress: Optional[Progress] = None
        self._live: Optional[Live] = None
        self._current_task_id: Optional[int] = None
        self._stage_start_time: float = 0
        self._characters: list[CharacterPreview] = []

    def create_progress_context(self) -> ProgressContext:
        """Create a progress context for reporting."""
        return ProgressContext(
            on_progress=self._on_progress,
            on_stage_complete=self._on_stage_complete,
        )

    def show_header(self, book_name: str) -> None:
        """Display the header panel."""
        header = Panel(
            Text(f"Regender-XYZ - {book_name}", justify="center", style="bold cyan"),
            border_style="cyan",
        )
        self.console.print(header)
        self.console.print()

    def _get_stage_description(self, stage: Stage) -> tuple[str, str]:
        """Get stage description and active form."""
        descriptions = {
            Stage.PARSING: ("Parsing text", "Parsing text..."),
            Stage.ANALYZING: ("Analyzing characters", "Analyzing characters..."),
            Stage.TRANSFORMING: ("Transforming chapters", "Transforming chapters..."),
            Stage.QUALITY_CONTROL: ("Quality control", "Running quality control..."),
        }
        return descriptions.get(stage, (stage.value, f"{stage.value}..."))

    def _on_progress(self, event: ProgressEvent) -> None:
        """Handle progress update events."""
        description, active_desc = self._get_stage_description(event.stage)

        # Start new progress display if needed
        if self._progress is None:
            self._stage_start_time = time.time()
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console,
                transient=False,
            )
            self._live = Live(self._progress, console=self.console, refresh_per_second=10)
            self._live.start()
            self._current_task_id = self._progress.add_task(active_desc, total=event.total)
        elif self._current_task_id is not None:
            # Check if we need to create a new task for a new stage
            task = self._progress.tasks[self._current_task_id]
            if not task.description.startswith(description.split()[0]):
                # New stage - complete old task and create new one
                self._progress.update(self._current_task_id, completed=task.total)
                self._stage_start_time = time.time()
                self._current_task_id = self._progress.add_task(active_desc, total=event.total)

        # Update progress
        if self._current_task_id is not None:
            self._progress.update(self._current_task_id, completed=event.current)

    def _on_stage_complete(self, event: StageCompleteEvent) -> None:
        """Handle stage completion events."""
        description, _ = self._get_stage_description(event.stage)

        # Stop live display temporarily
        if self._live:
            self._live.stop()
            self._progress = None
            self._live = None
            self._current_task_id = None

        # Build stats string
        stats_parts = []
        for key, value in event.stats.items():
            stats_parts.append(f"{key}: {value}")
        stats_str = ", ".join(stats_parts) if stats_parts else ""

        # Print completion message
        elapsed_str = f"{event.elapsed_seconds:.1f}s"
        if stats_str:
            self.console.print(f"  [green]✓[/green] {description} ({elapsed_str}) - {stats_str}")
        else:
            self.console.print(f"  [green]✓[/green] {description} ({elapsed_str})")

        # Show character preview if this is the analysis stage
        if event.stage == Stage.ANALYZING and event.characters:
            self._show_character_preview(event.characters)

        self.console.print()

    def _show_character_preview(self, characters: list[CharacterPreview]) -> None:
        """Display character transformation preview."""
        self.console.print()
        self.console.print(f"  Found {len(characters)} characters:")

        # Show up to MAX_CHARACTER_PREVIEW characters
        for char in characters[: self.MAX_CHARACTER_PREVIEW]:
            self.console.print(f"    [dim]•[/dim] {char}")

        # Show "and N more" if there are more characters
        remaining = len(characters) - self.MAX_CHARACTER_PREVIEW
        if remaining > 0:
            self.console.print(f"    [dim]... and {remaining} more[/dim]")

    def show_summary(
        self,
        elapsed_seconds: float,
        api_calls: int,
        tokens: int,
        output_path: str,
    ) -> None:
        """Display the final summary."""
        self.console.print("[green]✓ Transformation complete![/green]")
        self.console.print()

        # Format elapsed time
        if elapsed_seconds >= 60:
            minutes = int(elapsed_seconds // 60)
            seconds = int(elapsed_seconds % 60)
            elapsed_str = f"{minutes}m {seconds}s"
        else:
            elapsed_str = f"{elapsed_seconds:.1f}s"

        # Format tokens
        tokens_str = f"{tokens:,}" if tokens >= 1000 else str(tokens)

        # Build summary line
        summary_parts = [
            f"Elapsed: {elapsed_str}",
            f"API calls: {api_calls}",
            f"Tokens: {tokens_str}",
        ]
        self.console.print(f"  {' | '.join(summary_parts)}")
        self.console.print()
        self.console.print(f"  Output: [cyan]{output_path}[/cyan]")

    def show_error(self, message: str) -> None:
        """Display an error message."""
        # Stop any active progress display
        if self._live:
            self._live.stop()
            self._progress = None
            self._live = None

        self.console.print(f"[red]✗ Error: {message}[/red]")


class QuietDisplay(BaseDisplay):
    """Minimal display that only outputs the file path on success."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the display."""
        self.console = console or Console()
        self._output_path: Optional[str] = None

    def create_progress_context(self) -> ProgressContext:
        """Create a no-op progress context."""
        return ProgressContext()

    def show_header(self, book_name: str) -> None:
        """No-op for quiet mode."""
        pass

    def show_summary(
        self,
        elapsed_seconds: float,
        api_calls: int,
        tokens: int,
        output_path: str,
    ) -> None:
        """Output only the file path."""
        self.console.print(output_path)

    def show_error(self, message: str) -> None:
        """Display error to stderr."""
        self.console.print(f"Error: {message}", style="red", stderr=True)


class VerboseDisplay(CLIDisplay):
    """
    Rich display with additional debug information.

    Extends CLIDisplay to show progress bars plus debug logging.
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize the display."""
        super().__init__(console)

    def _on_progress(self, event: ProgressEvent) -> None:
        """Handle progress with additional debug output."""
        # Call parent implementation
        super()._on_progress(event)

        # In verbose mode, logging is enabled separately
        # This class just ensures the rich display works with verbose logging

    def _on_stage_complete(self, event: StageCompleteEvent) -> None:
        """Handle stage completion with additional debug output."""
        super()._on_stage_complete(event)

        # Show additional stats in verbose mode
        if event.stats:
            for key, value in event.stats.items():
                if key not in ["chapters", "paragraphs", "total_characters"]:
                    self.console.print(f"    [dim]{key}: {value}[/dim]")
