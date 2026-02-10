"""
Interactive CLI Mode

Provides a terminal-app-like interface for the Regender CLI.
"""

import os
import sys
import time
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
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from .app_display import AppDisplay


class ProjectPanel:
    """Manages the project info sidebar."""

    def __init__(self):
        self.book_title: Optional[str] = None
        self.book_path: Optional[Path] = None
        self.transform_type: Optional[str] = None
        self.status: str = "Ready"
        self.status_icon: str = "⏸"
        self.progress: float = 0.0
        self.progress_text: str = ""
        self.elapsed: float = 0.0
        self.remaining: Optional[float] = None
        self.characters: int = 0
        self.chapters_done: int = 0
        self.chapters_total: int = 0
        self.api_calls: int = 0
        self.tokens: int = 0
        self.output_path: Optional[str] = None

    def render(self) -> Panel:
        """Render the project panel."""
        sections = []

        # Book
        book_text = Text()
        book_text.append("📚 Book\n", style="bold cyan")
        if self.book_title:
            # Truncate long titles
            title = self.book_title[:25] + "..." if len(self.book_title) > 28 else self.book_title
            book_text.append(f"   {title}\n\n", style="white")
        else:
            book_text.append("   [dim]Not selected[/dim]\n\n")
        sections.append(book_text)

        # Transform
        transform_text = Text()
        transform_text.append("🔄 Transform\n", style="bold cyan")
        if self.transform_type:
            transform_text.append(f"   {self.transform_type}\n\n", style="white")
        else:
            transform_text.append("   [dim]Not selected[/dim]\n\n")
        sections.append(transform_text)

        # Status with progress bar
        status_text = Text()
        status_text.append(f"{self.status_icon} Status\n", style="bold cyan")
        status_text.append(f"   {self.status}\n")

        if self.progress > 0 and self.progress < 1:
            bar_width = 20
            filled = int(bar_width * self.progress)
            empty = bar_width - filled
            bar = "█" * filled + "░" * empty
            pct = int(self.progress * 100)
            status_text.append(f"   [green]{bar}[/green] {pct}%\n")

        if self.elapsed > 0:
            status_text.append(f"   [dim]⏱ {self._fmt_time(self.elapsed)}[/dim]")
            if self.remaining and self.remaining > 0:
                status_text.append(f" [dim]• ~{self._fmt_time(self.remaining)} left[/dim]")
            status_text.append("\n")

        status_text.append("\n")
        sections.append(status_text)

        # Stats (only if we have any)
        if self.characters or self.chapters_total or self.api_calls:
            stats_text = Text()
            stats_text.append("📊 Stats\n", style="bold cyan")
            if self.characters:
                stats_text.append(f"   Characters: {self.characters}\n")
            if self.chapters_total:
                stats_text.append(f"   Chapters: {self.chapters_done}/{self.chapters_total}\n")
            if self.api_calls:
                stats_text.append(f"   API calls: {self.api_calls}\n")
            if self.tokens:
                stats_text.append(f"   Tokens: {self.tokens:,}\n")
            stats_text.append("\n")
            sections.append(stats_text)

        # Output
        if self.output_path:
            out_text = Text()
            out_text.append("📄 Output\n", style="bold cyan")
            out_name = Path(self.output_path).name
            out_text.append(f"   [green]{out_name}[/green]\n\n")
            sections.append(out_text)

        return Panel(
            Group(*sections),
            title="[bold]PROJECT[/bold]",
            border_style="cyan",
            width=32,
        )

    def _fmt_time(self, secs: float) -> str:
        if secs < 60:
            return f"{int(secs)}s"
        elif secs < 3600:
            return f"{int(secs // 60)}m {int(secs % 60)}s"
        else:
            return f"{int(secs // 3600)}h {int((secs % 3600) // 60)}m"


class ReGenderApp:
    """Terminal-app-like interface for ReGender."""

    TRANSFORM_TYPES = [
        ("gender_swap", "Swap all genders"),
        ("all_male", "All characters → male"),
        ("all_female", "All characters → female"),
        ("nonbinary", "All characters → nonbinary"),
        ("parse_only", "Parse to JSON only"),
        ("character_analysis", "Analyze characters only"),
    ]

    def __init__(self):
        """Initialize the app."""
        self.console = Console()
        self.display = AppDisplay()
        # Keep panel for backward compatibility
        self.panel = self.display.state
        self.running = True

    def run(self) -> Optional[dict]:
        """Run in single-shot mode for CLI integration."""
        self.display.clear()
        return self._transform_flow()

    def _clear(self) -> None:
        """Clear screen."""
        self.display.clear()

    def _print_layout(self, main_content: str = "") -> None:
        """Print the split layout using AppDisplay."""
        self.display.main_content = [main_content] if main_content else []
        self.display.show_static()

    def _transform_flow(self) -> Optional[dict]:
        """Run the transformation selection flow."""
        # Select book
        book_path = self._select_book()
        if not book_path:
            return None

        book_title = self._get_book_title(book_path)
        self.display.set_book(book_title)

        # Select transformation
        transform_type = self._select_transform()
        if not transform_type:
            return None

        self.display.set_transform(transform_type)

        # Get options
        options = self._get_options(transform_type)
        if options is None:
            return None

        return {
            "input": str(book_path),
            "transform_type": transform_type,
            **options,
        }

    def _get_book_title(self, path: Path) -> str:
        """Extract a nice book title from path."""
        name = path.stem
        if name.startswith("pg") and "-" in name:
            name = name.split("-", 1)[1]
        return name.replace("_", " ").replace("-", " ").title()

    def _select_book(self) -> Optional[Path]:
        """Select a book."""
        sample = Path("books/texts/pride-prejudice-sample.txt")

        content = """
[bold]Select a book:[/bold]

  [dim]1.[/dim] Pride and Prejudice (sample)
  [dim]2.[/dim] [cyan]Enter file path...[/cyan]

"""
        self._clear()
        self._print_layout(content)

        while True:
            choice = Prompt.ask("[dim]book[/dim]", default="1")

            if choice.lower() in ("q", "quit"):
                return None

            if choice == "1":
                if sample.exists():
                    return sample
                self.console.print("[yellow]Sample not found[/yellow]")
            elif choice == "2":
                return self._get_path()
            else:
                # Try as direct path
                p = Path(choice).expanduser()
                if p.exists() and p.is_file():
                    return p
                self.console.print("[red]Enter 1, 2, or a file path[/red]")

    def _get_path(self) -> Optional[Path]:
        """Get a custom file path."""
        while True:
            path_str = Prompt.ask("[dim]path[/dim]")

            if path_str.lower() in ("q", "quit", "back"):
                return self._select_book()

            p = Path(path_str).expanduser()
            if p.exists() and p.is_file():
                return p
            elif p.exists():
                self.console.print("[red]That's a directory[/red]")
            else:
                self.console.print("[red]File not found[/red]")

    def _select_transform(self) -> Optional[str]:
        """Select transformation type."""
        lines = ["", "[bold]Select transformation:[/bold]", ""]
        for i, (name, desc) in enumerate(self.TRANSFORM_TYPES, 1):
            lines.append(f"  [dim]{i}.[/dim] [cyan]{name:<18}[/cyan] [dim]{desc}[/dim]")
        lines.append("")

        self._clear()
        self._print_layout("\n".join(lines))

        while True:
            choice = Prompt.ask("[dim]transform[/dim]", default="1")

            if choice.lower() in ("q", "quit", "back"):
                return None

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self.TRANSFORM_TYPES):
                    return self.TRANSFORM_TYPES[idx][0]
            except ValueError:
                # Check for name match
                for name, _ in self.TRANSFORM_TYPES:
                    if choice.lower() == name.lower():
                        return name

            self.console.print(f"[red]Enter 1-{len(self.TRANSFORM_TYPES)}[/red]")

    def _get_options(self, transform_type: str) -> Optional[dict]:
        """Get additional options."""
        options = {
            "no_qc": False,
            "verbose": False,
            "quiet": False,
            "output": None,
        }

        if transform_type not in ["parse_only", "character_analysis"]:
            self._clear()
            self._print_layout("\n[bold]Options:[/bold]\n")
            options["no_qc"] = not Confirm.ask("Run quality control?", default=True)

        return options

    def get_panel(self) -> ProjectPanel:
        """Get the project panel for external updates."""
        return ProjectPanel()  # Return empty panel for backward compat

    def get_display(self) -> AppDisplay:
        """Get the AppDisplay instance for continued use during processing."""
        return self.display


# Compatibility aliases
InteractiveMode = ReGenderApp


def run_interactive() -> tuple[Optional[dict], Optional[AppDisplay]]:
    """Run interactive mode. Returns (result, display) tuple."""
    app = ReGenderApp()
    result = app.run()
    return result, app.get_display()


def run_app_loop() -> None:
    """Run in persistent loop mode."""
    app = ReGenderApp()
    app.run()
