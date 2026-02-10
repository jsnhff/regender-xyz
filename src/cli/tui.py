"""
Textual TUI for Regender

A polished terminal user interface with fixed header, scrollable content,
and input footer - similar to Claude Code's interface.

Uses classic terminal green-on-black aesthetic.
"""

import os
import re
import time
from pathlib import Path
from typing import Callable, Optional

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.reactive import reactive
from textual.widgets import Input, Label, Static

from src.exporters import FORMATS, export_book
from src.progress import ProgressContext, ProgressEvent, Stage, StageCompleteEvent

# =============================================================================
# Book Analysis
# =============================================================================

# Cost per 1K tokens (input/output) by model
MODEL_COSTS = {
    "gpt-4": (0.03, 0.06),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-4o": (0.005, 0.015),
    "gpt-3.5-turbo": (0.001, 0.002),
    "claude-3-sonnet": (0.003, 0.015),
    "claude-3-haiku": (0.00025, 0.00125),
    "claude-3-opus": (0.015, 0.075),
    "claude-sonnet-4-20250514": (0.003, 0.015),
}


def analyze_book_file(path: Path) -> dict:
    """
    Quick analysis of a book file to estimate processing stats.

    Returns dict with: chapters, characters, words, pages, tokens, estimated_cost
    """
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return {}

    # Count chapters (look for common patterns)
    chapter_patterns = [
        r"^CHAPTER\s+[IVXLCDM\d]+",  # CHAPTER I, CHAPTER 1
        r"^Chapter\s+[IVXLCDM\d]+",
        r"^\d+\.\s+[A-Z]",  # 1. Title
    ]
    chapters = 0
    for pattern in chapter_patterns:
        matches = re.findall(pattern, text, re.MULTILINE)
        if matches:
            chapters = len(matches)
            break

    if chapters == 0:
        # Estimate from double newlines (paragraphs) - roughly 20 paragraphs per chapter
        paragraphs = len(re.split(r"\n\s*\n", text))
        chapters = max(1, paragraphs // 20)

    # Basic stats
    char_count = len(text)
    words = len(text.split())
    pages = max(1, words // 250)  # ~250 words per page

    # Estimate tokens (roughly 4 chars per token)
    tokens = char_count // 4

    # Estimate cost - assume ~2x tokens for output (transformation is verbose)
    # Use default model pricing (gpt-4o or claude-sonnet-4)
    model = os.environ.get("DEFAULT_MODEL", "gpt-4o")
    input_cost, output_cost = MODEL_COSTS.get(model, (0.005, 0.015))

    # For transformation: input is the book, output is roughly same size
    estimated_cost = (tokens / 1000 * input_cost) + (tokens / 1000 * output_cost)

    return {
        "chapters": chapters,
        "characters": char_count,
        "words": words,
        "pages": pages,
        "tokens": tokens,
        "estimated_cost": estimated_cost,
        "model": model,
    }


# =============================================================================
# Theme: Terminal Green
# =============================================================================

THEME_CSS = """
$primary: #00ff00;
$primary-dark: #00aa00;
$primary-dim: #005500;
$background: #000000;
$surface: #0a0a0a;
$text: #00ff00;
$text-muted: #00aa00;
$text-dim: #005500;
$success: #00ff00;
$error: #ff0000;
"""


# =============================================================================
# Widgets
# =============================================================================


LOGO_ART = "[bold #00ff00]regender[/bold #00ff00][#005500].xyz[/#005500]"

SPLASH_ART = """[bold #00ff00]
                                 _
  _ __ ___  __ _  ___ _ __   __| | ___ _ __  __  ___   _ ____
 | '__/ _ \\/ _` |/ _ \\ '_ \\ / _` |/ _ \\ '__| \\ \\/ / | | |_  /
 | | |  __/ (_| |  __/ | | | (_| |  __/ | _  >  <| |_| |/ /
 |_|  \\___|\\__, |\\___|_| |_|\\__,_|\\___|_|(_)/_/\\_\\\\__, /___|
           |___/                                  |___/
[/bold #00ff00]"""


class HeaderBar(Static):
    """Combined header with logo and status on line 1, metadata on line 2."""

    DEFAULT_CSS = """
    HeaderBar {
        dock: top;
        height: 4;
        background: #0a0a0a;
        padding: 0 2;
    }
    """

    def __init__(self, **kwargs):
        super().__init__("", **kwargs)  # Initialize with empty string
        self._book = "—"
        self._transform = "—"
        self._status = "Ready"
        self._meta = "─" * 60

    def on_mount(self) -> None:
        """Render initial content."""
        self._do_render()

    def _do_render(self) -> None:
        """Render the header content."""
        line1 = (
            f"{LOGO_ART}                    "
            f"[#005500]Book:[/#005500] [#00ff00]{self._book}[/#00ff00]  "
            f"[#005500]Transform:[/#005500] [#00ff00]{self._transform}[/#00ff00]  "
            f"[#005500]Status:[/#005500] [#00ff00]{self._status}[/#00ff00]"
        )
        line2 = "[#00aa00]" + "─" * 80 + "[/#00aa00]"
        line3 = f"[#005500]{self._meta}[/#005500]"
        line4 = "[#004400]" + "─" * 80 + "[/#004400]"
        self.update(Text.from_markup(f"{line1}\n{line2}\n{line3}\n{line4}"))

    def update_status(self, book: str = None, transform: str = None, status: str = None) -> None:
        """Update status fields."""
        if book is not None:
            self._book = book
        if transform is not None:
            self._transform = transform
        if status is not None:
            self._status = status
        self._do_render()

    def update_meta(self, stats: Optional[dict], char_count: Optional[int] = None) -> None:
        """Update metadata line."""
        if stats:
            parts = [
                f"~{stats['chapters']} chapters",
                f"~{stats['words']:,} words",
                f"~{stats['pages']} pages",
            ]
            if char_count is not None:
                parts.append(f"{char_count} characters")
            parts.append(f"Est. ${stats['estimated_cost']:.2f}")
            self._meta = " • ".join(parts)
        else:
            self._meta = "─" * 60
        self._do_render()


class ContentArea(ScrollableContainer):
    """Scrollable content area for logs."""

    DEFAULT_CSS = """
    ContentArea {
        height: 1fr;
        padding: 1 2;
        background: #000000;
        scrollbar-color: #003300;
        scrollbar-color-hover: #005500;
        scrollbar-color-active: #00aa00;
    }

    ContentArea .log-line {
        height: auto;
        margin: 0;
        padding: 0;
        color: #00ff00;
    }

    ContentArea .progress-line {
        height: auto;
        margin: 0;
        padding: 0;
        color: #00ff00;
    }
    """

    _progress_label: Optional[Label] = None

    def add_line(self, content: str) -> None:
        """Add a line to the content area."""
        label = Label(Text.from_markup(content), classes="log-line")
        self.mount(label)
        self.scroll_end(animate=False)

    def update_progress(self, content: str) -> None:
        """Update the progress line in place (or create if needed)."""
        if self._progress_label is None:
            self._progress_label = Label(Text.from_markup(content), classes="progress-line")
            self.mount(self._progress_label)
        else:
            self._progress_label.update(Text.from_markup(content))
        self.scroll_end(animate=False)

    def clear_progress(self) -> None:
        """Clear the progress line (convert to regular line or remove)."""
        self._progress_label = None


class InputBar(Static):
    """Fixed footer with input field."""

    DEFAULT_CSS = """
    InputBar {
        dock: bottom;
        height: 3;
        background: #0a0a0a;
        border-top: solid #003300;
        padding: 0 2;
    }

    InputBar > Horizontal {
        height: 100%;
        align: left middle;
    }

    InputBar #prompt {
        width: auto;
        color: #00aa00;
    }

    InputBar #input {
        width: 1fr;
        border: none;
        background: #0a0a0a;
        color: #00ff00;
        padding: 0;
    }

    InputBar #input:focus {
        border: none;
    }

    InputBar #input.-disabled {
        color: #005500;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(">  ", id="prompt")
            yield Input(placeholder="", id="input")

    def set_prompt(self, prompt: str) -> None:
        """Set the prompt text."""
        try:
            self.query_one("#prompt", Label).update(prompt)
        except Exception:
            pass

    def set_placeholder(self, text: str) -> None:
        """Set input placeholder."""
        try:
            self.query_one("#input", Input).placeholder = text
        except Exception:
            pass

    def disable(self) -> None:
        """Disable input."""
        try:
            inp = self.query_one("#input", Input)
            inp.disabled = True
        except Exception:
            pass

    def enable(self) -> None:
        """Enable input."""
        try:
            inp = self.query_one("#input", Input)
            inp.disabled = False
            inp.focus()
        except Exception:
            pass


class StatusBar(Static):
    """Simple status bar for processing mode."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: #0a0a0a;
        border-top: solid #003300;
        padding: 0 2;
        color: #00aa00;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Ready", id="message")

    def update(self, message: str) -> None:
        """Update status message."""
        try:
            self.query_one("#message", Label).update(message)
        except Exception:
            pass


# =============================================================================
# Main Application
# =============================================================================


class RegenderTUI(App):
    """
    Unified TUI for Regender.

    Handles both selection and processing in a single app instance,
    maintaining the UI throughout the entire flow.
    """

    CSS = """
    Screen {
        background: #000000;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Cancel"),
    ]

    TRANSFORM_TYPES = [
        ("gender_swap", "Swap all genders"),
        ("all_male", "All characters → male"),
        ("all_female", "All characters → female"),
        ("nonbinary", "All characters → nonbinary"),
        ("parse_only", "Parse to JSON only"),
        ("character_analysis", "Analyze characters only"),
    ]

    # State
    book_title: reactive[str] = reactive("—")
    transform_type: reactive[str] = reactive("—")
    status_text: reactive[str] = reactive("Ready")

    def __init__(self, process_callback: Optional[Callable] = None, **kwargs):
        super().__init__(**kwargs)
        self._process_callback = process_callback
        self._stage = "book"  # book, transform, options, processing, done
        self._selected_book: Optional[Path] = None
        self._selected_transform: Optional[str] = None
        self._no_qc = False
        self._result: Optional[dict] = None
        self._process_start: Optional[float] = None
        self._json_output_path: Optional[str] = None
        self._stage_start: Optional[float] = None
        self._current_stage: Optional[str] = None
        self._last_progress_line_id: Optional[str] = None
        self._book_stats: Optional[dict] = None
        self._analysis_running: bool = False

    def compose(self) -> ComposeResult:
        yield HeaderBar(id="header")
        yield ContentArea(id="content")
        yield InputBar()

    def on_mount(self) -> None:
        """Initialize the app."""
        self._update_header()
        # Show splash ASCII art
        for line in SPLASH_ART.strip().split("\n"):
            self.print(line)
        self.print("")
        self.print("[#005500]Transform gender representation in literature[/#005500]")
        self.print("")

        # Check LLM setup
        self._check_llm_setup()

        self._show_book_menu()
        self.query_one("#input", Input).focus()

    def _check_llm_setup(self) -> None:
        """Check if LLM provider is properly configured."""
        # Ensure .env is loaded
        from dotenv import load_dotenv

        load_dotenv()

        openai_key = os.environ.get("OPENAI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        provider = os.environ.get("DEFAULT_PROVIDER", "")

        has_openai = bool(openai_key and not openai_key.startswith("your-"))
        has_anthropic = bool(anthropic_key and not anthropic_key.startswith("your-"))

        if not has_openai and not has_anthropic:
            # No API keys configured
            self.print("[#ff6600]⚠ No API keys detected[/#ff6600]")
            self.print("")
            self.print(
                "[#005500]Add these to [/#005500][#00aa00].env[/#00aa00][#005500] in the project folder:[/#005500]"
            )
            self.print("")
            self.print("  [#00aa00]# For OpenAI:[/#00aa00]")
            self.print("  [#00ff00]OPENAI_API_KEY=sk-...[/#00ff00]")
            self.print("  [#00ff00]DEFAULT_PROVIDER=openai[/#00ff00]")
            self.print("")
            self.print("  [#00aa00]# Or for Anthropic:[/#00aa00]")
            self.print("  [#00ff00]ANTHROPIC_API_KEY=sk-ant-...[/#00ff00]")
            self.print("  [#00ff00]DEFAULT_PROVIDER=anthropic[/#00ff00]")
            self.print("")
            self.print(
                "[#005500]Then restart the app. You can still use 'parse_only' without keys.[/#005500]"
            )
            self.print("")
        elif not provider:
            # Has keys but no provider set
            available = []
            if has_openai:
                available.append("openai")
            if has_anthropic:
                available.append("anthropic")
            self.print("[#ff6600]⚠ DEFAULT_PROVIDER not set[/#ff6600]")
            self.print("")
            self.print(f"[#005500]You have API keys for: {', '.join(available)}[/#005500]")
            self.print(
                "[#005500]Add this to [/#005500][#00aa00].env[/#00aa00][#005500] in the project folder:[/#005500]"
            )
            self.print(f"  [#00ff00]DEFAULT_PROVIDER={available[0]}[/#00ff00]")
            self.print("")
        else:
            # All good - show which provider is active
            self.print(f"[#005500]Using {provider} for LLM calls[/#005500]")
            self.print("")

    # -------------------------------------------------------------------------
    # Header Updates
    # -------------------------------------------------------------------------

    def watch_book_title(self, value: str) -> None:
        self._update_header()

    def watch_transform_type(self, value: str) -> None:
        self._update_header()

    def watch_status_text(self, value: str) -> None:
        self._update_header()

    def _update_header(self) -> None:
        """Update all header columns."""
        try:
            header = self.query_one(HeaderBar)
            header.update_status(self.book_title, self.transform_type, self.status_text)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    def print(self, message: str) -> None:
        """Add a log line to the content area."""
        try:
            self.query_one("#content", ContentArea).add_line(message)
        except Exception:
            pass

    def set_prompt(self, prompt: str) -> None:
        """Set the input prompt."""
        try:
            self.query_one(InputBar).set_prompt(prompt)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Selection Flow
    # -------------------------------------------------------------------------

    def _show_book_menu(self) -> None:
        """Show book selection."""
        self._stage = "book"
        self.print("[#005500]? [/#005500][bold #00ff00]Select a book[/bold #00ff00]")
        self.print("")
        self.print("  [#00ff00]1[/#00ff00]  Pride and Prejudice [#005500](sample)[/#005500]")
        self.print("  [#00ff00]2[/#00ff00]  Enter file path...")
        self.print("")
        self.set_prompt(">  ")

    def _show_transform_menu(self) -> None:
        """Show transform selection."""
        self._stage = "transform"
        self.print("[#005500]? [/#005500][bold #00ff00]Select transformation[/bold #00ff00]")
        self.print("")
        for i, (name, desc) in enumerate(self.TRANSFORM_TYPES, 1):
            self.print(f"  [#00ff00]{i}[/#00ff00]  {name:<18} [#005500]{desc}[/#005500]")
        self.print("")
        self.set_prompt(">  ")

    def _show_options_menu(self) -> None:
        """Show options."""
        if self._selected_transform in ["parse_only", "character_analysis"]:
            self._start_processing()
            return

        self._stage = "options"
        self.print("[#005500]? [/#005500][bold #00ff00]Run quality control?[/bold #00ff00]")
        self.print("")
        self.print("  [#00ff00]Y[/#00ff00]  Yes [#005500](recommended)[/#005500]")
        self.print("  [#00ff00]n[/#00ff00]  No [#005500](faster)[/#005500]")
        self.print("")
        self.set_prompt(">  ")

    def _get_book_title(self, path: Path) -> str:
        """Extract book title from path."""
        name = path.stem
        if name.startswith("pg") and "-" in name:
            name = name.split("-", 1)[1]
        return name.replace("_", " ").replace("-", " ").title()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input."""
        value = event.value.strip()
        event.input.value = ""

        if self._stage == "book":
            self._handle_book_input(value)
        elif self._stage == "analyze_prompt":
            self._handle_analyze_prompt_input(value)
        elif self._stage == "transform":
            self._handle_transform_input(value)
        elif self._stage == "options":
            self._handle_options_input(value)
        elif self._stage == "export":
            self._handle_export_input(value)

    def _handle_book_input(self, value: str) -> None:
        """Handle book selection."""
        sample = Path("books/texts/pride-prejudice-sample.txt")

        if value == "1":
            if sample.exists():
                self._select_book(sample)
            else:
                self.print("[#ff0000]Sample not found[/#ff0000]")
        elif value == "2":
            self.set_prompt("path>  ")
        elif value.lower() in ("q", "quit"):
            self.exit()
        else:
            path = Path(value).expanduser()
            if path.exists() and path.is_file():
                self._select_book(path)
            elif path.exists():
                self.print("[#ff0000]That's a directory[/#ff0000]")
            else:
                self.print("[#ff0000]File not found[/#ff0000]")

    def _select_book(self, path: Path) -> None:
        """Select a book and show analysis."""
        self._selected_book = path
        self.book_title = self._get_book_title(path)
        self.print(f"[#00ff00]✓[/#00ff00] {self.book_title}")

        # Analyze the book and update header
        stats = analyze_book_file(path)
        if stats:
            self._book_stats = stats
            # Update header metadata row
            try:
                self.query_one(HeaderBar).update_meta(stats)
            except Exception:
                pass

        self.print("")
        self._show_character_analysis_prompt()

    def _show_character_analysis_prompt(self) -> None:
        """Ask if user wants to analyze characters first."""
        self._stage = "analyze_prompt"
        self.print("[#005500]? [/#005500][bold #00ff00]Analyze characters first?[/bold #00ff00]")
        self.print("")
        self.print(
            "  [#00ff00]Y[/#00ff00]  Yes [#005500](identifies characters, costs ~$0.02)[/#005500]"
        )
        self.print("  [#00ff00]n[/#00ff00]  No  [#005500](skip to transformation)[/#005500]")
        self.print("")
        self.set_prompt(">  ")

    def _handle_analyze_prompt_input(self, value: str) -> None:
        """Handle character analysis prompt."""
        if value.lower() in ("y", "yes", ""):
            self.print("[#00ff00]✓[/#00ff00] Analyzing characters")
            self.status_text = "Analyzing..."
            self._analysis_running = True
            self._run_character_analysis()
            self._run_analysis_spinner()
        else:
            self.print("[#00ff00]✓[/#00ff00] Skipped")
            self.print("")
            self._show_transform_menu()

    def _run_analysis_spinner(self) -> None:
        """Run a spinner animation while analysis is running."""
        import threading

        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        idx = 0

        def update_spinner():
            nonlocal idx
            while self._analysis_running:
                char = spinner_chars[idx % len(spinner_chars)]
                bar = "[#00ff00]" + "━" * 20 + "[/#00ff00][#003300]" + "━" * 20 + "[/#003300]"

                def do_update(c=char, b=bar):
                    try:
                        self.query_one("#content", ContentArea).update_progress(
                            f"  [#00aa00]{c} Analyzing[/#00aa00]  {b}"
                        )
                    except Exception:
                        pass

                self.call_from_thread(do_update)
                idx += 1
                time.sleep(0.1)

        thread = threading.Thread(target=update_spinner, daemon=True)
        thread.start()

    @work(exclusive=True, thread=True)
    def _run_character_analysis(self) -> None:
        """Run character analysis in background."""
        import asyncio
        import logging

        from dotenv import load_dotenv

        from src.app import Application

        # Load environment and suppress logging
        load_dotenv()
        logging.disable(logging.CRITICAL)

        # Create event loop for this thread (required by openai/anthropic SDKs)
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            app = Application("src/config.json")

            # Run character analysis
            result = app.analyze_characters_sync(
                file_path=str(self._selected_book),
                output_path=None,  # Don't save to file
            )

            app.shutdown()

            if result.get("success"):
                by_gender = result.get("by_gender", {})
                char_count = result.get("total_characters", 0)
                main_chars = result.get("main_characters", [])

                def show_results():
                    # Stop spinner and clear progress line
                    self._analysis_running = False
                    try:
                        self.query_one("#content", ContentArea).clear_progress()
                    except Exception:
                        pass
                    self.status_text = "Ready"

                    # Update header with character count
                    try:
                        self.query_one(HeaderBar).update_meta(self._book_stats, char_count)
                    except Exception:
                        pass

                    self.print(f"[#00ff00]✓[/#00ff00] Found {char_count} characters")

                    # Show gender breakdown
                    gender_parts = []
                    for gender, count in by_gender.items():
                        gender_parts.append(f"{count} {gender}")
                    if gender_parts:
                        self.print(f"  [#005500]Genders:[/#005500] {', '.join(gender_parts)}")

                    # Show top characters
                    if main_chars:
                        self.print("")
                        self.print("  [#005500]Main characters:[/#005500]")
                        for name in main_chars[:5]:
                            self.print(f"    [#00ff00]•[/#00ff00] {name}")
                        if len(main_chars) > 5:
                            self.print(f"    [#005500]... and {len(main_chars) - 5} more[/#005500]")

                    self.print("")
                    self._show_transform_menu()

                self.call_from_thread(show_results)
            else:
                error_msg = result.get("error", "Unknown error")

                def show_error():
                    # Stop spinner and clear progress
                    self._analysis_running = False
                    try:
                        self.query_one("#content", ContentArea).clear_progress()
                    except Exception:
                        pass
                    self.status_text = "Ready"

                    self.print(f"[#ff0000]Analysis failed:[/#ff0000] {error_msg}")
                    self._show_api_key_help(error_msg)
                    self.print("")
                    self._show_transform_menu()

                self.call_from_thread(show_error)

        except Exception as e:
            error_msg = str(e)

            def show_error():
                # Stop spinner and clear progress
                self._analysis_running = False
                try:
                    self.query_one("#content", ContentArea).clear_progress()
                except Exception:
                    pass
                self.status_text = "Ready"

                self.print(f"[#ff0000]Error:[/#ff0000] {error_msg}")
                self._show_api_key_help(error_msg)
                self.print("")
                self._show_transform_menu()

            self.call_from_thread(show_error)

    def _show_api_key_help(self, error_msg: str) -> None:
        """Show helpful message if error is about missing API keys."""
        if (
            "llm_provider" in error_msg.lower()
            or "not registered" in error_msg.lower()
            or "api" in error_msg.lower()
        ):
            self.print("")
            self.print(
                "[#005500]Add your API keys to [/#005500][#00aa00].env[/#00aa00][#005500] in the project folder:[/#005500]"
            )
            self.print("[#005500]  OPENAI_API_KEY=sk-...[/#005500]")
            self.print("[#005500]  DEFAULT_PROVIDER=openai[/#005500]")
            self.print("[#005500]Then restart the app.[/#005500]")

    def _handle_transform_input(self, value: str) -> None:
        """Handle transform selection."""
        if value.lower() in ("back", "b"):
            self._show_book_menu()
            return

        try:
            idx = int(value) - 1
            if 0 <= idx < len(self.TRANSFORM_TYPES):
                self._selected_transform = self.TRANSFORM_TYPES[idx][0]
                self.transform_type = self._selected_transform
                self.print(f"[#00ff00]✓[/#00ff00] {self._selected_transform}")
                self.print("")
                self._show_options_menu()
                return
        except ValueError:
            for name, _ in self.TRANSFORM_TYPES:
                if value.lower() == name.lower():
                    self._selected_transform = name
                    self.transform_type = name
                    self.print(f"[#00ff00]✓[/#00ff00] {name}")
                    self.print("")
                    self._show_options_menu()
                    return

        self.print(f"[#ff0000]Enter 1-{len(self.TRANSFORM_TYPES)}[/#ff0000]")

    def _handle_options_input(self, value: str) -> None:
        """Handle options."""
        if value.lower() in ("n", "no"):
            self._no_qc = True
            self.print("[#00ff00]✓[/#00ff00] QC disabled")
        else:
            self._no_qc = False
            self.print("[#00ff00]✓[/#00ff00] QC enabled")

        self.print("")
        self._start_processing()

    # -------------------------------------------------------------------------
    # Processing
    # -------------------------------------------------------------------------

    def _start_processing(self) -> None:
        """Start the transformation process."""
        self._stage = "processing"
        self._process_start = time.time()
        self.status_text = "Starting..."

        # Disable input during processing
        try:
            input_bar = self.query_one(InputBar)
            input_bar.set_prompt("[#005500]...[/#005500] ")
            input_bar.disable()
        except Exception:
            pass

        self.print("[#00aa00]Starting transformation...[/#00aa00]")
        self.print("")

        # Build result for callback
        self._result = {
            "input": str(self._selected_book),
            "transform_type": self._selected_transform,
            "no_qc": self._no_qc,
        }

        # Run processing in background worker
        if self._process_callback:
            self._run_processing()

    @work(exclusive=True, thread=True)
    def _run_processing(self) -> None:
        """Run processing in background thread."""
        try:
            result = self._process_callback(
                input_path=self._result["input"],
                transform_type=self._result["transform_type"],
                no_qc=self._result["no_qc"],
                progress_callback=self._on_progress,
                stage_callback=self._on_stage_complete,
            )

            # Show completion on main thread
            self.call_from_thread(self._show_complete, result)

        except Exception as e:
            self.call_from_thread(self._show_error, str(e))

    def _on_progress(self, event: ProgressEvent) -> None:
        """Handle progress update (called from worker thread)."""
        stage_names = {
            Stage.PARSING: "Parsing",
            Stage.ANALYZING: "Analyzing",
            Stage.TRANSFORMING: "Transforming",
            Stage.QUALITY_CONTROL: "QC",
        }
        stage_name = stage_names.get(event.stage, event.stage.value)
        pct = (event.current / event.total) if event.total > 0 else 0
        pct_int = int(pct * 100)

        # Track stage timing for ETA
        now = time.time()
        if self._current_stage != stage_name:
            self._current_stage = stage_name
            self._stage_start = now

        # Calculate ETA
        eta_str = ""
        if self._stage_start and event.current > 0:
            elapsed = now - self._stage_start
            rate = event.current / elapsed
            if rate > 0:
                remaining = (event.total - event.current) / rate
                if remaining < 60:
                    eta_str = f" [#005500]~{int(remaining)}s left[/#005500]"
                else:
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    eta_str = f" [#005500]~{mins}m {secs}s left[/#005500]"

        # Build progress bar
        bar_width = 40
        filled = int(bar_width * pct)
        empty = bar_width - filled
        bar = "[#00ff00]" + "━" * filled + "[/#00ff00][#003300]" + "━" * empty + "[/#003300]"

        def update():
            self.status_text = f"{stage_name} {pct_int}%"
            # Update progress line in place
            progress_line = f"  [#00aa00]{stage_name:<14}[/#00aa00] {bar} [#00ff00]{pct_int:>3}%[/#00ff00]{eta_str}"
            try:
                self.query_one("#content", ContentArea).update_progress(progress_line)
            except Exception:
                pass

        self.call_from_thread(update)

    def _on_stage_complete(self, event: StageCompleteEvent) -> None:
        """Handle stage complete (called from worker thread)."""
        stage_names = {
            Stage.PARSING: "Parsing",
            Stage.ANALYZING: "Analyzing",
            Stage.TRANSFORMING: "Transforming",
            Stage.QUALITY_CONTROL: "Quality Check",
        }
        stage_name = stage_names.get(event.stage, event.stage.value)
        stats = ", ".join(f"{k}: {v}" for k, v in event.stats.items()) if event.stats else ""

        def update():
            # Clear the in-place progress line
            try:
                self.query_one("#content", ContentArea).clear_progress()
            except Exception:
                pass

            # Add completion message as permanent line
            msg = f"[#00ff00]✓[/#00ff00] {stage_name} [#005500]({event.elapsed_seconds:.1f}s)[/#005500]"
            if stats:
                msg += f" [#005500]— {stats}[/#005500]"
            self.print(msg)
            self.status_text = f"{stage_name} ✓"

        self.call_from_thread(update)

    def _show_complete(self, result: dict) -> None:
        """Show completion and export options (called on main thread)."""
        elapsed = time.time() - self._process_start if self._process_start else 0

        self.print("")
        self.print("[bold #00ff00]✓ Transformation complete![/bold #00ff00]")
        self.print(f"  [#005500]Time:[/#005500] {elapsed:.1f}s")

        # Store JSON path for export
        self._json_output_path = result.get("output_path")

        if self._json_output_path:
            self.print(f"  [#005500]JSON:[/#005500] [#00ff00]{self._json_output_path}[/#00ff00]")

        # Show export options
        self._stage = "export"
        self.print("")
        self.print("[#005500]? [/#005500][bold #00ff00]Export format[/bold #00ff00]")
        self.print("")
        self.print("  [#00ff00]1[/#00ff00]  txt  [#005500]Plain text (UTF-8)[/#005500]")
        self.print("  [#00ff00]2[/#00ff00]  rtf  [#005500]Rich Text Format (InDesign)[/#005500]")
        self.print("  [#00ff00]3[/#00ff00]  skip [#005500]JSON only[/#005500]")
        self.print("")

        self.status_text = "Export?"

        # Re-enable input for export selection
        try:
            input_bar = self.query_one(InputBar)
            input_bar.set_prompt(">  ")
            input_bar.enable()
        except Exception:
            pass

    def _handle_export_input(self, value: str) -> None:
        """Handle export format selection."""
        if value in ("3", "skip", "s", ""):
            self.print("[#00ff00]✓[/#00ff00] Skipped export")
            self._show_final()
            return

        format_map = {
            "1": "txt",
            "txt": "txt",
            "text": "txt",
            "2": "rtf",
            "rtf": "rtf",
        }

        format_key = format_map.get(value.lower())
        if not format_key:
            self.print("[#ff0000]Enter 1, 2, or 3[/#ff0000]")
            return

        if not self._json_output_path:
            self.print("[#ff0000]No JSON output to export[/#ff0000]")
            self._show_final()
            return

        # Do the export
        try:
            from pathlib import Path

            json_path = Path(self._json_output_path)
            output_path = export_book(str(json_path), format_key)
            self.print(f"[#00ff00]✓[/#00ff00] Exported to [#00ff00]{output_path}[/#00ff00]")
        except Exception as e:
            self.print(f"[#ff0000]Export error:[/#ff0000] {e}")

        self._show_final()

    def _show_final(self) -> None:
        """Show final message and disable input."""
        self._stage = "done"
        self.print("")
        self.print("[#005500]Press Ctrl+C to exit[/#005500]")
        self.status_text = "Complete ✓"

        try:
            input_bar = self.query_one(InputBar)
            input_bar.set_prompt("[#005500]✓[/#005500]  ")
            input_bar.disable()
        except Exception:
            pass

    def _show_error(self, error: str) -> None:
        """Show error (called on main thread)."""
        self._stage = "done"
        self.print("")
        self.print(f"[bold #ff0000]✗ Error:[/bold #ff0000] {error}")
        self.print("")
        self.status_text = "Error"

    def create_progress_context(self) -> ProgressContext:
        """Create progress context for external use."""
        return ProgressContext(
            on_progress=self._on_progress,
            on_stage_complete=self._on_stage_complete,
        )

    def get_result(self) -> Optional[dict]:
        """Get the selection result."""
        return self._result


# =============================================================================
# Entry Points
# =============================================================================


def run_tui(process_callback: Optional[Callable] = None) -> Optional[dict]:
    """
    Run the full TUI experience.

    Args:
        process_callback: Function to call for processing. Should accept:
            - input_path: str
            - transform_type: str
            - no_qc: bool
            - progress_callback: Callable
            - stage_callback: Callable

    Returns:
        Result dict or None if cancelled.
    """
    app = RegenderTUI(process_callback=process_callback)
    app.run()
    return app.get_result()


def run_selection() -> Optional[dict]:
    """Run selection only (no processing), return result for external processing."""
    app = RegenderTUI(process_callback=None)
    app.run()
    return app.get_result()
