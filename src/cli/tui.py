"""
Textual TUI for Regender

A polished terminal user interface with fixed header, scrollable content,
and input footer.
"""

import math
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
# Gradient Text Utilities
# =============================================================================


def gradient_text(text: str, colors: list[str]) -> str:
    """Create gradient text by applying different colors to each character."""
    if len(text) == 0:
        return ""
    if len(colors) < 2:
        return f"[{colors[0]}]{text}[/]"

    result = []
    steps = len(text)
    color_steps = len(colors) - 1

    for i, char in enumerate(text):
        # Determine which color to use based on position
        progress = i / max(1, steps - 1)
        color_index = progress * color_steps
        lower_idx = int(color_index)
        lower_idx = min(lower_idx, len(colors) - 1)
        color = colors[lower_idx]
        result.append(f"[{color}]{char}[/]")

    return "".join(result)


# Smooth 2-color gradient palettes
MAGENTA_PINK = ["#ff006e", "#ff0080", "#ff1a8c", "#ff3399", "#ff4da6", "#ff66b3", "#ff80c0", "#ff99cc"]
CYAN_BLUE = ["#00f5ff", "#00d4ff", "#00b3ff", "#0099ff", "#007fff", "#0066ff", "#004dff", "#0033ff"]
YELLOW_ORANGE = ["#ffbe0b", "#ffb00a", "#ffa209", "#ff9408", "#ff8607", "#ff7806", "#ff6a05", "#ff5c04"]
VIOLET_MAGENTA = ["#8338ec", "#9033e8", "#9d2ee4", "#aa29e0", "#b724dc", "#c41fd8", "#d11ad4", "#de15d0"]
PINK_VIOLET = ["#ff006e", "#f01a82", "#e13396", "#d24daa", "#c366be", "#b480d2", "#a599e6", "#96b3fa"]
FIRE_GLOW = ["#ff006e", "#ff3355", "#ff5c3d", "#ff8526", "#ffae0f"]


# =============================================================================
# Book Analysis
# =============================================================================

# Cost per 1K tokens (input/output) by model
def _get_resolved_model() -> str:
    """
    Resolve the actual model used by the provider (mirrors unified_provider logic).
    Uses DEFAULT_MODEL if set, else OPENAI_MODEL/ANTHROPIC_MODEL based on DEFAULT_PROVIDER.
    """
    model = os.environ.get("DEFAULT_MODEL")
    if model:
        return model
    provider = os.environ.get("DEFAULT_PROVIDER", "openai")
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-5-20251101")
    return os.environ.get("OPENAI_MODEL", "gpt-5")


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
    # Resolve actual model from provider config (same logic as unified_provider)
    model = _get_resolved_model()
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
# Theme: Bold Saturated Colors
# =============================================================================

THEME_CSS = """
$primary: #ff006e;        /* Hot magenta */
$secondary: #00f5ff;      /* Electric cyan */
$accent: #ffbe0b;         /* Bold yellow */
$violet: #8338ec;         /* Deep violet */
$background: #0a0014;     /* Deep purple-black */
$surface: #1a0028;        /* Slightly lighter purple */
$text: #ffffff;           /* Pure white */
$text-dim: #b8a0cc;       /* Lavender dim */
$success: #00f5ff;        /* Cyan */
$error: #ff006e;          /* Magenta */
"""


# =============================================================================
# Widgets
# =============================================================================


# Logo with smooth magenta→pink gradient
LOGO_ART = gradient_text("regender", MAGENTA_PINK) + "[#8338ec].xyz[/]"



class SineWaveLoader(Static):
    """Animated sine wave loader - shows activity during processing."""

    DEFAULT_CSS = """
    SineWaveLoader {
        height: 3;
        padding: 0;
        margin: 0;
    }
    """

    def __init__(self, message: str = "Processing", **kwargs):
        super().__init__("", **kwargs)
        self._message = message
        self._frame = 0
        self._running = False

    def on_mount(self) -> None:
        """Start the animation."""
        self._running = True
        self.set_interval(0.05, self._update_frame)

    def _update_frame(self) -> None:
        """Update animation frame."""
        if self._running:
            self._frame += 1
            self._render_wave()

    def _render_wave(self) -> None:
        """Render the sine wave at current frame."""
        try:
            width = 60
            height_chars = "▁▂▃▄▅▆▇█"
            # Smooth cyan→blue gradient for the wave
            wave_colors = ["#00f5ff", "#00d4ff", "#00b3ff", "#0099ff", "#007fff", "#0066ff"]

            # Generate sine wave
            wave = []
            for x in range(width):
                # Two sine waves offset for more complex pattern
                y1 = math.sin((x + self._frame) * 0.2) * 3
                y2 = math.sin((x - self._frame) * 0.15) * 2
                y = (y1 + y2) / 2

                # Map to character
                char_idx = int((y + 3) / 6 * len(height_chars))
                char_idx = max(0, min(len(height_chars) - 1, char_idx))

                # Color based on position (smooth gradient across wave)
                color_idx = int((x / width) * (len(wave_colors) - 1))
                color = wave_colors[color_idx]

                wave.append(f"[{color}]{height_chars[char_idx]}[/]")

            # Message with gradient
            msg = gradient_text(self._message, VIOLET_MAGENTA)

            # Compose output
            wave_str = "".join(wave)
            output = f"{msg}\n{wave_str}"

            self.update(Text.from_markup(output))
        except Exception:
            pass  # Gracefully handle rendering errors

    def stop(self) -> None:
        """Stop the animation."""
        self._running = False


class HeaderBar(Container):
    """Clean structured header using Grid for automatic alignment."""

    DEFAULT_CSS = """
    HeaderBar {
        dock: top;
        height: 6;
        background: #1a0028;
        padding: 0 1;
        border-bottom: heavy #00f5ff;
    }

    HeaderBar #top-bar {
        width: 100%;
        height: 1;
    }

    HeaderBar #version {
        dock: right;
        width: auto;
    }

    HeaderBar #border1, HeaderBar #border2 {
        width: 100%;
        height: 1;
        color: #00f5ff;
    }

    HeaderBar #stats-row1, HeaderBar #stats-row2 {
        width: 100%;
        height: 1;
    }

    HeaderBar #stats-row1 > Label, HeaderBar #stats-row2 > Label {
        width: 1fr;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._book = "—"
        self._transform = "—"
        self._pages = "—"
        self._chapters = "—"
        self._characters = "—"
        self._model = "—"
        self._cost = "—"

    def compose(self) -> ComposeResult:
        # Top bar: logo, tagline, version
        with Horizontal(id="top-bar"):
            tagline_text = "transform characters' gender in books"
            tagline_gradient = gradient_text(tagline_text, CYAN_BLUE)
            yield Label(f"{LOGO_ART}  {tagline_gradient}")
            yield Label("[#b8a0cc]v1.0[/]", id="version")

        # Border
        yield Label("─" * 100, id="border1")

        # Row 1: book stats
        with Horizontal(id="stats-row1"):
            yield Label(f"[#b8a0cc]book:[/] [#00f5ff]{self._book}[/]")
            yield Label(f"[#b8a0cc]pages:[/] [#ffbe0b]{self._pages}[/]")
            yield Label(f"[#b8a0cc]chapters:[/] [#ff006e]{self._chapters}[/]")
            yield Label(f"[#b8a0cc]characters:[/] [#8338ec]{self._characters}[/]")

        # Border
        yield Label("─" * 100, id="border2")

        # Row 2: processing info
        with Horizontal(id="stats-row2"):
            yield Label(f"[#b8a0cc]transformation:[/] [#00f5ff]{self._transform}[/]")
            yield Label(f"[#b8a0cc]model:[/] [#ffbe0b]{self._model}[/]")
            yield Label(f"[#b8a0cc]total cost:[/] [#ff006e]{self._cost}[/]")

    def update_status(self, book: str = None, transform: str = None, status: str = None) -> None:
        """Update book and transform fields."""
        if book is not None:
            self._book = book
        if transform is not None:
            self._transform = transform
        self._refresh()

    def update_meta(self, stats: Optional[dict], char_count: Optional[int] = None) -> None:
        """Update all metadata fields."""
        if stats:
            self._pages = str(stats.get('pages', '—'))
            self._chapters = str(stats.get('chapters', '—'))
            self._cost = f"${stats.get('estimated_cost', 0):.2f}"
            self._model = stats.get('model', '—')

        if char_count is not None:
            self._characters = str(char_count)

        self._refresh()

    def _refresh(self) -> None:
        """Update all labels with current values."""
        try:
            labels = self.query("#stats-row1 > Label")
            if len(labels) >= 4:
                labels[0].update(Text.from_markup(f"[#b8a0cc]book:[/] [#00f5ff]{self._book}[/]"))
                labels[1].update(Text.from_markup(f"[#b8a0cc]pages:[/] [#ffbe0b]{self._pages}[/]"))
                labels[2].update(Text.from_markup(f"[#b8a0cc]chapters:[/] [#ff006e]{self._chapters}[/]"))
                labels[3].update(Text.from_markup(f"[#b8a0cc]characters:[/] [#8338ec]{self._characters}[/]"))

            labels = self.query("#stats-row2 > Label")
            if len(labels) >= 3:
                labels[0].update(Text.from_markup(f"[#b8a0cc]transformation:[/] [#00f5ff]{self._transform}[/]"))
                labels[1].update(Text.from_markup(f"[#b8a0cc]model:[/] [#ffbe0b]{self._model}[/]"))
                labels[2].update(Text.from_markup(f"[#b8a0cc]total cost:[/] [#ff006e]{self._cost}[/]"))
        except Exception:
            pass


class ContentArea(ScrollableContainer):
    """Scrollable content area with artistic scrollbar."""

    DEFAULT_CSS = """
    ContentArea {
        height: 1fr;
        padding: 1 1;
        background: #0a0014;
        scrollbar-color: #8338ec;
        scrollbar-color-hover: #ff006e;
        scrollbar-color-active: #00f5ff;
    }

    ContentArea .log-line {
        height: auto;
        margin: 0;
        padding: 0;
        color: #ffffff;
    }

    ContentArea .progress-line {
        height: auto;
        margin: 0;
        padding: 0;
        color: #ffffff;
    }
    """

    _progress_label: Optional[Label] = None

    def add_line(self, content: str) -> None:
        """Add a line to the content area."""
        label = Label(Text.from_markup(content), classes="log-line")
        self.mount(label)
        self.scroll_end(animate=False)

    def add_widget(self, widget: Static) -> None:
        """Add a widget (like SineWaveLoader) to the content area."""
        self.mount(widget)
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


# Braille 6-dot loading animation (clockwise rotation)
BRAILLE_LOADING_FRAMES = ["⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇"]


class BrailleLoader(Static):
    """Braille loading animation with elapsed time for LLM activities."""

    DEFAULT_CSS = """
    BrailleLoader {
        height: 1;
        padding: 0;
        margin: 0;
    }
    """

    def __init__(self, activity: str, start_time: float, **kwargs):
        super().__init__("", **kwargs)
        self._activity = activity
        self._start_time = start_time
        self._frame = 0
        self._running = False

    def on_mount(self) -> None:
        """Start the animation."""
        self._running = True
        self.set_interval(0.12, self._update_frame)

    def _update_frame(self) -> None:
        """Update animation frame and elapsed time."""
        if self._running:
            self._frame += 1
            elapsed = int(time.time() - self._start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            if mins > 0:
                time_str = f"{mins}m {secs}s"
            else:
                time_str = f"{secs}s"

            frame_char = BRAILLE_LOADING_FRAMES[self._frame % len(BRAILLE_LOADING_FRAMES)]
            msg = f"[#00f5ff]{frame_char}[/] [#b8a0cc]{self._activity}[/] [#ffbe0b]({time_str})[/]"
            self.update(Text.from_markup(msg))

    def stop(self) -> None:
        """Stop the animation."""
        self._running = False


class InputBar(Static):
    """Clean input bar matching the layout design."""

    DEFAULT_CSS = """
    InputBar {
        dock: bottom;
        height: 2;
        background: #1a0028;
        border-top: heavy #00f5ff;
        padding: 0 1;
    }

    InputBar > Horizontal {
        height: 100%;
        align: left middle;
    }

    InputBar #prompt {
        width: auto;
        color: #00f5ff;
    }

    InputBar #input {
        width: 1fr;
        border: none;
        background: #1a0028;
        color: #00f5ff;
        padding: 0;
    }

    InputBar #input:focus {
        border: none;
        color: #ffbe0b;
    }

    InputBar #input.-disabled {
        color: #b8a0cc;
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

    def start_loading_animation(self) -> None:
        """Start animated braille loading indicator in the prompt."""
        self._loading_frame = 0

        def tick() -> None:
            frame = BRAILLE_LOADING_FRAMES[self._loading_frame % len(BRAILLE_LOADING_FRAMES)]
            self.set_prompt(f"[#00f5ff]{frame}[/] ")
            self._loading_frame += 1

        self._loading_interval = self.set_interval(0.12, tick)

    def stop_loading_animation(self, restore: str = ">  ") -> None:
        """Stop loading animation and restore prompt."""
        if hasattr(self, "_loading_interval") and self._loading_interval:
            self._loading_interval.stop()
            self._loading_interval = None
        self.set_prompt(restore)


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
        self._output_path: Optional[Path] = None
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

        # Simple welcome message
        self.print("[#00f5ff]◆[/] [#b8a0cc]Welcome to regender.xyz[/]")
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
            self.print("[bold #ffbe0b]⚠ No API keys detected[/]")
            self.print("")
            self.print(
                "[#b8a0cc]Add these to[/] [bold #00f5ff].env[/] [#b8a0cc]in the project folder:[/]"
            )
            self.print("")
            self.print("  [#8338ec]# For OpenAI:[/]")
            self.print("  [#00f5ff]OPENAI_API_KEY=sk-...[/]")
            self.print("  [#00f5ff]DEFAULT_PROVIDER=openai[/]")
            self.print("")
            self.print("  [#8338ec]# Or for Anthropic:[/]")
            self.print("  [#00f5ff]ANTHROPIC_API_KEY=sk-ant-...[/]")
            self.print("  [#00f5ff]DEFAULT_PROVIDER=anthropic[/]")
            self.print("")
            self.print(
                "[#b8a0cc]Then restart the app. You can still use 'parse_only' without keys.[/]"
            )
            self.print("")
        elif not provider:
            # Has keys but no provider set
            available = []
            if has_openai:
                available.append("openai")
            if has_anthropic:
                available.append("anthropic")
            self.print("[bold #ffbe0b]⚠ DEFAULT_PROVIDER not set[/]")
            self.print("")
            self.print(f"[#b8a0cc]You have API keys for: {', '.join(available)}[/]")
            self.print(
                "[#b8a0cc]Add this to[/] [bold #00f5ff].env[/] [#b8a0cc]in the project folder:[/]"
            )
            self.print(f"  [#00f5ff]DEFAULT_PROVIDER={available[0]}[/]")
            self.print("")
        else:
            # All good - show which provider is active
            self.print(f"[#00f5ff]◆[/] [#b8a0cc]Using {provider} for LLM calls[/]")
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
        """Show book selection with colorful styling."""
        self._stage = "book"
        self.print("[#8338ec]?[/] [bold #ff006e]Select a book[/]")
        self.print("")
        self.print("  [bold #00f5ff]1[/]  Pride and Prejudice [#b8a0cc](sample)[/]")
        self.print("  [bold #00f5ff]2[/]  Enter file path...")
        self.print("")
        self.set_prompt(">  ")

    def _show_transform_menu(self) -> None:
        """Show transform selection with colorful styling."""
        self._stage = "transform"
        self.print("[#8338ec]?[/] [bold #ff006e]Select transformation[/]")
        self.print("")
        for i, (name, desc) in enumerate(self.TRANSFORM_TYPES, 1):
            self.print(f"  [bold #00f5ff]{i}[/]  {name:<18} [#b8a0cc]{desc}[/]")
        self.print("")
        self.set_prompt(">  ")

    def _show_options_menu(self) -> None:
        """Show options with colorful styling."""
        # Calculate and show output path
        self._calculate_output_path()
        self.print("")
        self.print("[#b8a0cc]Output will be saved to:[/]")
        self.print(f"  [#00f5ff]{self._output_path}[/]")
        self.print("")

        # TODO: Re-enable QC prompt once app.process_book() supports
        # a quality_control parameter. Currently QC is commented out
        # in app.py (line 323), so the prompt was cosmetic.
        self._no_qc = True
        self._start_processing()

    def _get_book_title(self, path: Path) -> str:
        """Extract book title from path."""
        name = path.stem
        if name.startswith("pg") and "-" in name:
            name = name.split("-", 1)[1]
        return name.replace("_", " ").replace("-", " ").title()

    def _calculate_output_path(self) -> None:
        """Calculate and store the output path based on current selections."""
        if not self._selected_book or not self._selected_transform:
            return

        input_file = self._selected_book
        book_name = input_file.stem

        # Remove common prefixes like pg12- or pg43-
        if book_name.startswith("pg") and "-" in book_name:
            book_name = book_name.split("-", 1)[1]

        # Convert to lowercase and replace spaces/underscores with hyphens
        book_folder = book_name.lower().replace("_", "-").replace(" ", "-")

        if self._selected_transform == "parse_only":
            # For parsing: keep in books/json/ with same name
            if "texts" in str(input_file.parent):
                output_dir = Path(str(input_file.parent).replace("texts", "json"))
            else:
                output_dir = input_file.parent
            self._output_path = output_dir / f"{input_file.stem}.json"
        elif self._selected_transform == "character_analysis":
            # For character analysis: save to book's output folder
            output_dir = Path("books/output") / book_folder
            output_dir.mkdir(parents=True, exist_ok=True)
            self._output_path = output_dir / "characters.json"
        else:
            # For transformations: save to book's output folder with transformation type
            output_dir = Path("books/output") / book_folder
            output_dir.mkdir(parents=True, exist_ok=True)
            self._output_path = output_dir / f"{self._selected_transform}.json"

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
        self.print(f"[#00f5ff]✓[/] {self.book_title}")

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
        self.print("[#8338ec]?[/] [bold #ff006e]Analyze characters first?[/]")
        self.print("")
        self.print(
            "  [bold #00f5ff]Y[/]  Yes [#b8a0cc](identifies characters, costs ~$0.02)[/]"
        )
        self.print("  [bold #00f5ff]n[/]  No  [#b8a0cc](skip to transformation)[/]")
        self.print("")
        self.set_prompt(">  ")

    def _handle_analyze_prompt_input(self, value: str) -> None:
        """Handle character analysis prompt."""
        if value.lower() in ("y", "yes", ""):
            self._analysis_running = True
            self._analysis_start_time = time.time()
            self.status_text = "Analyzing..."

            # Add braille loader with elapsed time
            self._analysis_loader = BrailleLoader("Analyzing characters", self._analysis_start_time)
            try:
                self.query_one("#content", ContentArea).add_widget(self._analysis_loader)
            except Exception:
                pass

            self._run_character_analysis()
        else:
            self.print("[#00f5ff]✓[/] Skipped")
            self.print("")
            self._show_transform_menu()

    @work(exclusive=True)
    async def _run_character_analysis(self) -> None:
        """Run character analysis as async worker on Textual's event loop."""
        import logging
        import sys
        import traceback

        from dotenv import load_dotenv

        # Set up file-based debug logging (TUI owns the terminal)
        debug_log = logging.getLogger("tui_debug")
        debug_log.setLevel(logging.DEBUG)
        debug_log.handlers.clear()
        from pathlib import Path as _P

        _P("logs").mkdir(exist_ok=True)
        _fh = logging.FileHandler("logs/tui_debug.log", mode="a")
        _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        debug_log.addHandler(_fh)

        # Undo global logging.disable(CRITICAL) set by _launch_tui()
        logging.disable(logging.NOTSET)

        debug_log.info("=" * 60)
        debug_log.info("CHARACTER ANALYSIS START")
        debug_log.info(f"Python {sys.version}")
        debug_log.info(f"Platform: {sys.platform}")
        debug_log.info(f"Book: {self._selected_book}")

        # Load environment
        load_dotenv()
        debug_log.info("dotenv loaded")

        # Patch tqdm: its multiprocessing lock triggers fds_to_keep
        # on macOS Python 3.9 inside Textual. Replace with threading lock.
        import threading
        import tqdm.std
        tqdm.std.TqdmDefaultWriteLock.create_mp_lock = classmethod(
            lambda cls: setattr(cls, "mp_lock", threading.RLock())
        )
        debug_log.info("tqdm mp_lock patched to threading.RLock")

        # Suppress noisy library logs but keep our debug logger
        logging.getLogger("anthropic").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

        try:
            debug_log.info("Creating Application...")
            from src.app import Application

            app = Application("src/config.json")
            debug_log.info("Application created OK")

            # --- Inline the steps so we get full tracebacks ---
            debug_log.info("Step 1: Getting parser service...")
            parser = app.get_service("parser")
            debug_log.info(f"  parser = {type(parser).__name__}")

            debug_log.info("Step 2: Parsing book...")
            book = await parser.process(str(self._selected_book))
            debug_log.info(f"  book parsed: {book.title}, {len(book.chapters)} chapters")

            debug_log.info("Step 3: Getting character service...")
            character_service = app.get_service("character")
            debug_log.info(f"  character_service = {type(character_service).__name__}")

            debug_log.info("Step 4: Analyzing characters (LLM call)...")
            characters = await character_service.process(book)
            debug_log.info(f"  found {len(characters.characters)} characters")

            stats = characters.get_statistics()
            result = {
                "success": True,
                "book_title": book.title,
                "total_characters": stats["total"],
                "by_gender": stats["by_gender"],
                "by_importance": stats["by_importance"],
                "main_characters": stats["main_characters"],
            }
            debug_log.info(f"Analysis complete: {result}")

            app.shutdown()
            debug_log.info("App shutdown OK")

            if result.get("success"):
                by_gender = result.get("by_gender", {})
                char_count = result.get("total_characters", 0)
                main_chars = result.get("main_characters", [])

                def show_results():
                    # Stop braille loader
                    self._analysis_running = False
                    if hasattr(self, '_analysis_loader'):
                        try:
                            self._analysis_loader.stop()
                            self._analysis_loader.remove()
                        except Exception:
                            pass
                    self.status_text = "Ready"

                    # Calculate elapsed time
                    elapsed = time.time() - self._analysis_start_time if hasattr(self, '_analysis_start_time') else 0

                    # Update header with character count
                    try:
                        self.query_one(HeaderBar).update_meta(self._book_stats, char_count)
                    except Exception:
                        pass

                    self.print(f"[#00f5ff]✓[/] Found [bold #00f5ff]{char_count}[/] characters [#b8a0cc]({elapsed:.1f}s)[/]")

                    # Show gender breakdown
                    gender_parts = []
                    for gender, count in by_gender.items():
                        gender_parts.append(f"{count} {gender}")
                    if gender_parts:
                        self.print(f"  [#b8a0cc]Genders:[/] {', '.join(gender_parts)}")

                    # Show top characters
                    if main_chars:
                        self.print("")
                        self.print("  [#b8a0cc]Main characters:[/]")
                        for name in main_chars[:5]:
                            self.print(f"    [#00f5ff]•[/] {name}")
                        if len(main_chars) > 5:
                            self.print(f"    [#b8a0cc]... and {len(main_chars) - 5} more[/]")

                    self.print("")
                    self._show_transform_menu()

                show_results()
            else:
                error_msg = result.get("error", "Unknown error")
                debug_log.error(f"Analysis returned failure: {error_msg}")
                # Stop braille loader
                self._analysis_running = False
                if hasattr(self, '_analysis_loader'):
                    try:
                        self._analysis_loader.stop()
                        self._analysis_loader.remove()
                    except Exception:
                        pass
                self.status_text = "Ready"

                self.print(f"\n[#ff006e]Analysis failed:[/] {error_msg}")
                self.print("[#b8a0cc]  See logs/tui_debug.log for details[/]")
                self._show_api_key_help(error_msg)
                self.print("")
                self._show_transform_menu()

        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            debug_log.error(f"Analysis EXCEPTION: {error_msg}")
            debug_log.error(f"Full traceback:\n{tb}")
            # Stop braille loader (exception case)
            self._analysis_running = False
            if hasattr(self, '_analysis_loader'):
                try:
                    self._analysis_loader.stop()
                    self._analysis_loader.remove()
                except Exception:
                    pass
            self.status_text = "Ready"

            self.print(f"\n[#ff006e]Error:[/] {error_msg}")
            self.print("[#b8a0cc]  See logs/tui_debug.log for full traceback[/]")
            self._show_api_key_help(error_msg)
            self.print("")
            self._show_transform_menu()

    def _show_api_key_help(self, error_msg: str) -> None:
        """Show helpful message if error is about missing API keys."""
        if (
            "llm_provider" in error_msg.lower()
            or "not registered" in error_msg.lower()
            or "api" in error_msg.lower()
        ):
            self.print("")
            self.print(
                "[#b8a0cc]Add your API keys to[/] [bold #00f5ff].env[/] [#b8a0cc]in the project folder:[/]"
            )
            self.print("[#b8a0cc]  OPENAI_API_KEY=sk-...[/]")
            self.print("[#b8a0cc]  DEFAULT_PROVIDER=openai[/]")
            self.print("[#b8a0cc]Then restart the app.[/]")

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

    def _show_stage_loader(self, stage_name: str, start_time: float) -> None:
        """Show braille loader for a stage."""
        def show_loader():
            # Stop any existing loader
            if hasattr(self, '_stage_loader') and self._stage_loader:
                try:
                    self._stage_loader.stop()
                    self._stage_loader.remove()
                except Exception:
                    pass

            # Show new braille loader
            self._stage_loader = BrailleLoader(stage_name, start_time)
            try:
                self.query_one("#content", ContentArea).add_widget(self._stage_loader)
            except Exception:
                pass

        # Delay slightly so if progress bars appear quickly, we don't show the loader
        self.call_later(0.3, show_loader)

    def _start_processing(self) -> None:
        """Start the transformation process."""
        self._stage = "processing"
        self._process_start = time.time()
        self.status_text = "Starting..."

        # Disable input during processing
        try:
            input_bar = self.query_one(InputBar)
            input_bar.start_loading_animation()
            input_bar.disable()
        except Exception:
            pass

        self.print(f"{gradient_text('Starting transformation', FIRE_GLOW)}...")

        # Show braille loader with elapsed timer
        self._transform_loader = BrailleLoader("Transforming", self._process_start)
        try:
            self.query_one("#content", ContentArea).add_widget(self._transform_loader)
        except Exception:
            pass

        self.print("")

        # Build result for callback
        self._result = {
            "input": str(self._selected_book),
            "transform_type": self._selected_transform,
            "no_qc": self._no_qc,
            "output_path": str(self._output_path) if self._output_path else None,
        }

        # Run processing in background worker
        self._run_processing()

    @work(exclusive=True)
    async def _run_processing(self) -> None:
        """Run processing as async worker on Textual's event loop."""
        import logging
        import traceback

        # Set up file-based debug logging
        debug_log = logging.getLogger("tui_debug")
        debug_log.setLevel(logging.DEBUG)
        if not debug_log.handlers:
            from pathlib import Path as _P

            _P("logs").mkdir(exist_ok=True)
            _fh = logging.FileHandler("logs/tui_debug.log", mode="a")
            _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            debug_log.addHandler(_fh)

        # Undo global logging.disable(CRITICAL) set by _launch_tui()
        logging.disable(logging.NOTSET)

        debug_log.info("=" * 60)
        debug_log.info("TRANSFORMATION START")
        debug_log.info(f"Input: {self._result.get('input')}")
        debug_log.info(f"Transform: {self._result.get('transform_type')}")
        debug_log.info(f"Output: {self._result.get('output_path')}")

        # Patch tqdm: its multiprocessing lock triggers fds_to_keep
        # on macOS Python 3.9 inside Textual. Replace with threading lock.
        import threading
        import tqdm.std
        tqdm.std.TqdmDefaultWriteLock.create_mp_lock = classmethod(
            lambda cls: setattr(cls, "mp_lock", threading.RLock())
        )

        # Suppress noisy library logs but keep our debug logger
        logging.getLogger("anthropic").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

        try:
            debug_log.info("Creating Application...")
            from src.app import Application

            app = Application("src/config.json")
            debug_log.info("Application created OK")

            debug_log.info("Calling process_book (await)...")
            result = await app.process_book(
                file_path=self._result["input"],
                transform_type=self._result["transform_type"],
                output_path=self._result.get("output_path"),
            )
            debug_log.info(f"process_book returned: success={result.get('success')}")

            app.shutdown()
            debug_log.info("App shutdown OK")
            self._show_complete(result)

        except Exception as e:
            tb = traceback.format_exc()
            debug_log.error(f"Transformation EXCEPTION: {e}")
            debug_log.error(f"Full traceback:\n{tb}")
            self._show_error(f"{e}\n  See logs/tui_debug.log for full traceback")

    def _on_progress(self, event: ProgressEvent) -> None:
        """Handle progress update with gradient progress bars."""
        # Stop any active stage loader when we get progress
        if hasattr(self, '_stage_loader') and self._stage_loader:
            try:
                self._stage_loader.stop()
                self._stage_loader.remove()
                self._stage_loader = None
            except Exception:
                pass

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
            # Show braille loader for this stage (will be replaced by progress bar)
            self._show_stage_loader(stage_name, now)

        # Calculate ETA
        eta_str = ""
        if self._stage_start and event.current > 0:
            elapsed = now - self._stage_start
            rate = event.current / elapsed
            if rate > 0:
                remaining = (event.total - event.current) / rate
                if remaining < 60:
                    eta_str = f" [#b8a0cc]~{int(remaining)}s left[/]"
                else:
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    eta_str = f" [#b8a0cc]~{mins}m {secs}s left[/]"

        # Build gradient progress bar (magenta→pink)
        bar_width = 50
        filled = int(bar_width * pct)
        empty = bar_width - filled

        # Gradient colors for filled portion
        gradient_colors = ["#ff006e", "#ff1a8c", "#ff3399", "#ff4da6", "#ff66b3", "#ff80c0", "#ff99cc"]
        filled_chars = []
        for i in range(filled):
            progress_in_fill = i / max(1, filled - 1) if filled > 1 else 0
            color_idx = int(progress_in_fill * (len(gradient_colors) - 1))
            color = gradient_colors[color_idx]
            filled_chars.append(f"[{color}]━[/]")

        filled_str = "".join(filled_chars)
        empty_str = f"[#8338ec]{'━' * empty}[/]"
        bar = filled_str + empty_str

        # Percentage color based on completion
        if pct < 0.3:
            pct_color = "#ff006e"
        elif pct < 0.7:
            pct_color = "#ffbe0b"
        else:
            pct_color = "#00f5ff"

        # Stage name with gradient
        stage_gradient = gradient_text(stage_name, CYAN_BLUE)

        def update():
            self.status_text = f"{stage_name} {pct_int}%"
            # Update progress line in place
            progress_line = f"  {stage_gradient:<25} {bar} [{pct_color}]{pct_int:>3}%[/]{eta_str}"
            try:
                self.query_one("#content", ContentArea).update_progress(progress_line)
            except Exception:
                pass

        self.call_from_thread(update)

    def _on_stage_complete(self, event: StageCompleteEvent) -> None:
        """Handle stage complete with colorful styling."""
        stage_names = {
            Stage.PARSING: "Parsing",
            Stage.ANALYZING: "Analyzing",
            Stage.TRANSFORMING: "Transforming",
            Stage.QUALITY_CONTROL: "Quality Check",
        }
        stage_name = stage_names.get(event.stage, event.stage.value)
        stats = ", ".join(f"{k}: {v}" for k, v in event.stats.items()) if event.stats else ""

        def update():
            # Stop any active stage loader
            if hasattr(self, '_stage_loader') and self._stage_loader:
                try:
                    self._stage_loader.stop()
                    self._stage_loader.remove()
                    self._stage_loader = None
                except Exception:
                    pass

            # Clear the in-place progress line
            try:
                self.query_one("#content", ContentArea).clear_progress()
            except Exception:
                pass

            # Add completion message with gradient
            stage_gradient = gradient_text(stage_name, CYAN_BLUE)
            msg = f"[#00f5ff]✓[/] {stage_gradient} [#b8a0cc]({event.elapsed_seconds:.1f}s)[/]"
            if stats:
                msg += f" [#b8a0cc]— {stats}[/]"
            self.print(msg)
            self.status_text = f"{stage_name} ✓"

        self.call_from_thread(update)

    def _show_complete(self, result: dict) -> None:
        """Show completion and export options (called on main thread)."""
        elapsed = time.time() - self._process_start if self._process_start else 0

        # Check if transformation actually succeeded
        if not result.get("success", False):
            error_msg = result.get("error", "Transformation failed")
            self._show_error(error_msg)
            return

        # Check if output file exists
        output_path = result.get("output_path")
        if output_path and Path(output_path).exists():
            self._json_output_path = output_path
        else:
            # Transformation said it succeeded but no file exists
            self.print("")
            self.print("[#ffbe0b]⚠ Transformation completed but output file not found[/]")
            self.print(f"  [#b8a0cc]Expected:[/] {output_path}")
            self.print(f"  [#b8a0cc]Time:[/] {elapsed:.1f}s (suspicious if < 5s)")
            self.print("")
            self._json_output_path = None
            self._show_final()
            return

        # Stop transform loader
        if hasattr(self, '_transform_loader') and self._transform_loader:
            try:
                self._transform_loader.stop()
                self._transform_loader.remove()
                self._transform_loader = None
            except Exception:
                pass

        self.print("")
        self.print(f"[#00f5ff]✓[/] {gradient_text('Transformation complete!', FIRE_GLOW)}")
        self.print(f"  [#b8a0cc]Time:[/] [#ffbe0b]{elapsed:.1f}s[/]")
        self.print(f"  [#b8a0cc]Saved:[/] [#00f5ff]{self._json_output_path}[/]")

        # Show export options from FORMATS
        self._stage = "export"
        self._export_format_list = list(FORMATS.keys())
        self.print("")
        self.print("[#8338ec]?[/] [bold #ff006e]Export format[/]")
        self.print("")
        for i, key in enumerate(self._export_format_list, 1):
            info = FORMATS[key]
            self.print(f"  [bold #00f5ff]{i}[/]  {key:<15} [#b8a0cc]{info['description']}[/]")
        skip_num = len(self._export_format_list) + 1
        self.print(f"  [bold #00f5ff]{skip_num}[/]  skip [#b8a0cc](JSON only)[/]")
        self.print("")

        self.status_text = "Export?"

        # Re-enable input for export selection
        try:
            input_bar = self.query_one(InputBar)
            input_bar.stop_loading_animation()
            input_bar.enable()
        except Exception:
            pass

    def _handle_export_input(self, value: str) -> None:
        """Handle export format selection."""
        value = (value or "").strip()
        format_list = getattr(self, "_export_format_list", None) or list(FORMATS.keys())
        skip_num = len(format_list) + 1
        if value in (str(skip_num), "skip", "s", ""):
            self.print("[#00f5ff]✓[/] Skipped export")
            self._show_final()
            return

        format_map = {str(i): k for i, k in enumerate(format_list, 1)}
        format_map.update({k: k for k in format_list})
        format_map["text"] = "txt"
        format_key = format_map.get(value.lower() if value else "")
        if not format_key:
            self.print(f"[#ff006e]Enter 1-{skip_num} or format key[/]")
            return

        if not self._json_output_path:
            self.print("[#ffbe0b]⚠[/] [#b8a0cc]No JSON output path available. Transformation may have saved to a different location.[/]")
            self._show_final()
            return

        # Do the export
        try:
            from pathlib import Path

            json_path = Path(self._json_output_path)
            output_path = export_book(str(json_path), format_key)
            self.print(f"[#00f5ff]✓[/] Exported to [#00f5ff]{output_path}[/]")
        except Exception as e:
            self.print(f"[#ff006e]Export error:[/] {e}")

        self._show_final()

    def _show_final(self) -> None:
        """Show final message and disable input."""
        self._stage = "done"
        self.print("")
        self.print("[#b8a0cc]Press Ctrl+C to exit[/]")
        self.status_text = "Complete ✓"

        try:
            input_bar = self.query_one(InputBar)
            input_bar.stop_loading_animation(restore="[#00f5ff]✓[/]  ")
            input_bar.disable()
        except Exception:
            pass

    def _show_error(self, error: str) -> None:
        """Show error (called on main thread)."""
        self._stage = "done"

        # Stop any active loaders
        for attr in ('_transform_loader', '_stage_loader', '_analysis_loader'):
            loader = getattr(self, attr, None)
            if loader:
                try:
                    loader.stop()
                    loader.remove()
                except Exception:
                    pass
                setattr(self, attr, None)

        self.print("")
        self.print(f"[bold #ff0000]✗ Error:[/bold #ff0000] {error}")
        self.print("")
        self.status_text = "Error"
        try:
            input_bar = self.query_one(InputBar)
            input_bar.stop_loading_animation(restore="[#ff006e]✗[/]  ")
        except Exception:
            pass

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
