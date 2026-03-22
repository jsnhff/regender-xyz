"""
Textual TUI for Regender

A polished terminal user interface with fixed header, scrollable content,
and input footer.
"""

import contextlib
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
MAGENTA_PINK = [
    "#00ff00",
    "#ff0080",
    "#ff1a8c",
    "#ff3399",
    "#ff4da6",
    "#ff66b3",
    "#ff80c0",
    "#ff99cc",
]
CYAN_BLUE = ["#00ff00", "#00d4ff", "#00b3ff", "#0099ff", "#007fff", "#0066ff", "#004dff", "#0033ff"]
YELLOW_ORANGE = [
    "#00ff00",
    "#ffb00a",
    "#ffa209",
    "#ff9408",
    "#ff8607",
    "#ff7806",
    "#ff6a05",
    "#ff5c04",
]
VIOLET_MAGENTA = [
    "#00ff00",
    "#9033e8",
    "#9d2ee4",
    "#aa29e0",
    "#b724dc",
    "#c41fd8",
    "#d11ad4",
    "#de15d0",
]
PINK_VIOLET = [
    "#00ff00",
    "#f01a82",
    "#e13396",
    "#d24daa",
    "#c366be",
    "#b480d2",
    "#a599e6",
    "#96b3fa",
]
FIRE_GLOW = ["#00ff00", "#ff3355", "#ff5c3d", "#ff8526", "#ffae0f"]


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
    return os.environ.get("OPENAI_MODEL", "gpt-4o")


# (input, output) cost per 1M tokens — updated Feb 2026
MODEL_COSTS = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (3.00, 12.00),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (1.00, 2.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-opus-4-5": (5.00, 25.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
}


def _lookup_model_cost(model: str) -> tuple[float, float]:
    """Match model string to cost table, using prefix matching for dated variants."""
    if model in MODEL_COSTS:
        return MODEL_COSTS[model]
    for key in MODEL_COSTS:
        if model.startswith(key):
            return MODEL_COSTS[key]
    return (3.00, 15.00)


# Fallback model list — used when live API fetch fails
_FALLBACK_MODELS: dict[str, list[tuple[str, str, str]]] = {
    "anthropic": [
        ("claude-opus-4-5-20251101", "Claude Opus 4.5", "$5 / $25 per 1M tokens"),
        ("claude-sonnet-4-20250514", "Claude Sonnet 4", "$3 / $15 per 1M tokens"),
    ],
    "openai": [
        ("gpt-4o", "GPT-4o", "$2.50 / $10 per 1M tokens"),
        ("gpt-4o-mini", "GPT-4o Mini", "$0.15 / $0.60 per 1M tokens"),
    ],
}

# Keep AVAILABLE_MODELS as alias for backwards compat
AVAILABLE_MODELS = _FALLBACK_MODELS

# OpenAI model ID prefixes suitable for text generation
_OPENAI_SHOW_PREFIXES = ("gpt-4", "gpt-3.5-turbo", "o1", "o3", "o4")
# Sub-patterns that indicate embedding / audio / image / fine-tuning models
_OPENAI_SKIP_PATTERNS = (
    "instruct",
    "realtime",
    "audio",
    "tts",
    "whisper",
    "dall-e",
    "embedding",
    "search",
)


def _should_show_openai_model(model_id: str) -> bool:
    """Return True if this OpenAI model is suitable for text generation."""
    if any(s in model_id for s in _OPENAI_SKIP_PATTERNS):
        return False
    return any(model_id.startswith(p) for p in _OPENAI_SHOW_PREFIXES)


def _openai_display_name(model_id: str) -> str:
    """Convert an OpenAI model ID to a short display name."""
    for mid, name, _ in _FALLBACK_MODELS.get("openai", []):
        if mid == model_id:
            return name
    # Generic: gpt-4o-mini → GPT-4o Mini, o3-mini → O3 Mini
    name = model_id
    for prefix, replacement in (("gpt-", "GPT-"), ("o1", "O1"), ("o3", "O3"), ("o4", "O4")):
        if name.startswith(prefix):
            name = replacement + name[len(prefix) :]
            break
    return name.replace("-", " ")


def _friendly_model_name(model: str) -> str:
    """Convert API model ID to a short display name."""
    all_models = [m for models in _FALLBACK_MODELS.values() for m in models]
    for model_id, display_name, _ in all_models:
        if model == model_id:
            return display_name
    for model_id, display_name, _ in sorted(all_models, key=lambda m: -len(m[0])):
        if model.startswith(model_id):
            return display_name
    return model


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

    model = _get_resolved_model()
    input_cost, output_cost = _lookup_model_cost(model)

    # Input = book text + prompts, output ~ same size as book
    estimated_cost = (tokens / 1_000_000 * input_cost) + (tokens / 1_000_000 * output_cost)

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
$primary: #00ff00;        /* Hot magenta */
$secondary: #00ff00;      /* Electric cyan */
$accent: #00ff00;         /* Bold yellow */
$violet: #00ff00;         /* Deep violet */
$background: #000000;     /* Black */
$surface: #000000;        /* Black */
$text: #00ff00;           /* Green */
$text-dim: #00aa00;       /* Lavender dim */
$success: #00ff00;        /* Cyan */
$error: #00ff00;          /* Magenta */
"""


# =============================================================================
# Widgets
# =============================================================================


# Green gradient palette for header
GREEN_GRADIENT = ["#00ff00", "#00dd00", "#00bb00", "#00aa00", "#008800"]

# Logo - green gradient on black
LOGO_ART = gradient_text("regender", GREEN_GRADIENT) + gradient_text(".xyz", ["#00aa00", "#00ff00"])


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
            # Green gradient for the wave
            wave_colors = ["#00ff00", "#00dd00", "#00bb00", "#009900", "#007700", "#005500"]

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

            # Message with green
            msg = gradient_text(self._message, ["#00ff00", "#00aa00"])

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
        background: #000000;
        border-bottom: heavy #00ff00;
        padding: 0;
    }

    HeaderBar #top-bar {
        width: 100vw;
        height: 1;
        background: #000000;
    }

    HeaderBar #top-bar-content {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    HeaderBar #stats-row1,
    HeaderBar #stats-row2 {
        width: 100%;
        height: 1;
        padding: 0 1;
    }

    HeaderBar #version {
        dock: right;
        width: auto;
    }

    HeaderBar #border1, HeaderBar #border2 {
        width: 100%;
        height: 1;
        color: #00ff00;
    }

    HeaderBar #stats-row1 > Label, HeaderBar #stats-row2 > Label {
        width: 1fr;
    }

    HeaderBar #stats-row1 > Label:first-child, HeaderBar #stats-row2 > Label:first-child {
        width: 2fr;
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
        # Top bar: black background, green gradient text
        with Horizontal(id="top-bar"), Horizontal(id="top-bar-content"):
            tagline = gradient_text("transform characters' gender in books", GREEN_GRADIENT)
            yield Label(f"{LOGO_ART}  {tagline}")
            yield Label(gradient_text("v1.0", ["#00aa00", "#00ff00"]), id="version")

        # Border (wide enough for large terminals)
        yield Label("─" * 200, id="border1")

        # Row 1: book stats
        with Horizontal(id="stats-row1"):
            yield Label(f"[#00aa00]book:[/] [#00ff00]{self._book}[/]")
            yield Label(f"[#00aa00]pages:[/] [#00ff00]{self._pages}[/]")
            yield Label(f"[#00aa00]chapters:[/] [#00ff00]{self._chapters}[/]")
            yield Label(f"[#00aa00]characters:[/] [#00ff00]{self._characters}[/]")

        # Border (wide enough for large terminals)
        yield Label("─" * 200, id="border2")

        # Row 2: processing info
        with Horizontal(id="stats-row2"):
            yield Label(f"[#00aa00]transformation:[/] [#00ff00]{self._transform}[/]")
            yield Label(f"[#00aa00]model:[/] [#00ff00]{self._model}[/]")
            yield Label(f"[#00aa00]total cost:[/] [#00ff00]{self._cost}[/]")

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
            self._pages = str(stats.get("pages", "—"))
            self._chapters = str(stats.get("chapters", "—"))
            self._cost = f"${stats.get('estimated_cost', 0):.2f}"
            raw_model = stats.get("model", "—")
            self._model = _friendly_model_name(raw_model) if raw_model != "—" else "—"

        if char_count is not None:
            self._characters = str(char_count)

        self._refresh()

    def _refresh(self) -> None:
        """Update all labels with current values."""
        try:
            labels = self.query("#stats-row1 > Label")
            if len(labels) >= 4:
                labels[0].update(Text.from_markup(f"[#00aa00]book:[/] [#00ff00]{self._book}[/]"))
                labels[1].update(Text.from_markup(f"[#00aa00]pages:[/] [#00ff00]{self._pages}[/]"))
                labels[2].update(
                    Text.from_markup(f"[#00aa00]chapters:[/] [#00ff00]{self._chapters}[/]")
                )
                labels[3].update(
                    Text.from_markup(f"[#00aa00]characters:[/] [#00ff00]{self._characters}[/]")
                )

            labels = self.query("#stats-row2 > Label")
            if len(labels) >= 3:
                labels[0].update(
                    Text.from_markup(f"[#00aa00]transformation:[/] [#00ff00]{self._transform}[/]")
                )
                labels[1].update(Text.from_markup(f"[#00aa00]model:[/] [#00ff00]{self._model}[/]"))
                labels[2].update(
                    Text.from_markup(f"[#00aa00]total cost:[/] [#00ff00]{self._cost}[/]")
                )
        except Exception:
            pass


class ContentArea(ScrollableContainer):
    """Scrollable content area with artistic scrollbar."""

    DEFAULT_CSS = """
    ContentArea {
        height: 1fr;
        padding: 1 1;
        background: #000000;
        scrollbar-color: #00aa00;
        scrollbar-color-hover: #00ff00;
        scrollbar-color-active: #00ff00;
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
            time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

            frame_char = BRAILLE_LOADING_FRAMES[self._frame % len(BRAILLE_LOADING_FRAMES)]
            msg = f"[#00ff00]{frame_char}[/] [#00aa00]{self._activity}[/] [#00ff00]({time_str})[/]"
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
        background: #000000;
        border-top: heavy #00ff00;
        padding: 0 1;
    }

    InputBar > Horizontal {
        height: 100%;
        align: left middle;
    }

    InputBar #prompt {
        width: auto;
        color: #00ff00;
    }

    InputBar #input {
        width: 1fr;
        border: none;
        background: #000000;
        color: #00ff00;
        padding: 0;
    }

    InputBar #input:focus {
        border: none;
        color: #00ff00;
    }

    InputBar #input.-disabled {
        color: #00aa00;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label(">  ", id="prompt")
            yield Input(placeholder="", id="input")

    def set_prompt(self, prompt: str) -> None:
        """Set the prompt text."""
        with contextlib.suppress(Exception):
            self.query_one("#prompt", Label).update(prompt)

    def set_placeholder(self, text: str) -> None:
        """Set input placeholder."""
        with contextlib.suppress(Exception):
            self.query_one("#input", Input).placeholder = text

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
            self.set_prompt(f"[#00ff00]{frame}[/] ")
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
        background: #000000;
        border-top: solid #00ff00;
        padding: 0 2;
        color: #00ff00;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Ready", id="message")

    def update(self, message: str) -> None:
        """Update status message."""
        with contextlib.suppress(Exception):
            self.query_one("#message", Label).update(message)


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
        padding: 0;
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
        self.print("[#00ff00]◆[/] [#00aa00]Welcome to regender.xyz[/]")
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
            self.print("[bold #00ff00]⚠ No API keys detected[/]")
            self.print("")
            self.print(
                "[#00aa00]Add these to[/] [bold #00ff00].env[/] [#00aa00]in the project folder:[/]"
            )
            self.print("")
            self.print("  [#00ff00]# For OpenAI:[/]")
            self.print("  [#00ff00]OPENAI_API_KEY=sk-...[/]")
            self.print("  [#00ff00]DEFAULT_PROVIDER=openai[/]")
            self.print("")
            self.print("  [#00ff00]# Or for Anthropic:[/]")
            self.print("  [#00ff00]ANTHROPIC_API_KEY=sk-ant-...[/]")
            self.print("  [#00ff00]DEFAULT_PROVIDER=anthropic[/]")
            self.print("")
            self.print(
                "[#00aa00]Then restart the app. You can still use 'parse_only' without keys.[/]"
            )
            self.print("")
        elif not provider:
            # Has keys but no provider set
            available = []
            if has_openai:
                available.append("openai")
            if has_anthropic:
                available.append("anthropic")
            self.print("[bold #00ff00]⚠ DEFAULT_PROVIDER not set[/]")
            self.print("")
            self.print(f"[#00aa00]You have API keys for: {', '.join(available)}[/]")
            self.print(
                "[#00aa00]Add this to[/] [bold #00ff00].env[/] [#00aa00]in the project folder:[/]"
            )
            self.print(f"  [#00ff00]DEFAULT_PROVIDER={available[0]}[/]")
            self.print("")
        else:
            # All good - show which provider is active
            self.print(f"[#00ff00]◆[/] [#00aa00]Using {provider} for LLM calls[/]")
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
        with contextlib.suppress(Exception):
            self.query_one("#content", ContentArea).add_line(message)

    def set_prompt(self, prompt: str) -> None:
        """Set the input prompt."""
        with contextlib.suppress(Exception):
            self.query_one(InputBar).set_prompt(prompt)

    # -------------------------------------------------------------------------
    # Selection Flow
    # -------------------------------------------------------------------------

    def _show_book_menu(self) -> None:
        """Show book selection with colorful styling."""
        self._stage = "book"
        self.print("[#00ff00]?[/] [bold #00ff00]Select a book[/]")
        self.print("")
        self.print("  [bold #00ff00]1[/]  Pride and Prejudice [#00aa00](sample)[/]")
        self.print("  [bold #00ff00]2[/]  Enter or drag file path...")
        self.print("")
        self.set_prompt(">  ")

    def _show_transform_menu(self) -> None:
        """Show transform selection with colorful styling."""
        self._stage = "transform"
        self.print("[#00ff00]?[/] [bold #00ff00]Select transformation[/]")
        self.print("")
        for i, (name, desc) in enumerate(self.TRANSFORM_TYPES, 1):
            self.print(f"  [bold #00ff00]{i}[/]  {name:<18} [#00aa00]{desc}[/]")
        self.print("")
        self.set_prompt(">  ")

    def _show_options_menu(self) -> None:
        """Show output path and quality control option."""
        self._calculate_output_path()
        self.print("")
        self.print("[#00aa00]Output will be saved to:[/]")
        self.print(f"  [#00ff00]{self._output_path}[/]")
        self.print("")
        self._stage = "options"
        self.print("[#00ff00]?[/] [bold #00ff00]Apply quality control?[/]")
        self.print("")
        pass1_cost = self._estimate_cost_str(0.8)
        pass2_cost = self._estimate_cost_str(0.4)
        # Compute combined total if both are available
        if self._book_stats:
            tokens = self._book_stats.get("tokens", 0)
            model = os.environ.get("DEFAULT_MODEL", "")
            input_cost, output_cost = _lookup_model_cost(model)
            combined = tokens * 1.2 / 1_000_000 * (input_cost + output_cost)
            total_cost_str = f"~${combined:.2f}"
        else:
            total_cost_str = ""
        self.print("  [bold #00ff00]Y[/]  Yes [#00aa00]— two-pass review:[/]")
        pass1_suffix = f" [#00aa00]({pass1_cost})[/]" if pass1_cost else ""
        pass2_suffix = f" [#00aa00]({pass2_cost})[/]" if pass2_cost else ""
        total_suffix = f" [#00aa00](~{total_cost_str} total)[/]" if total_cost_str else ""
        self.print(
            f"       [#00aa00]Pass 1  paragraph scan — catches missed pronouns & honorifics[/]{pass1_suffix}"
        )
        self.print(
            f"       [#00aa00]Pass 2  character audit — verifies each character throughout the full book[/]{pass2_suffix}"
        )
        if total_suffix:
            self.print(f"       [#00aa00]Estimated cost:[/]{total_suffix}")
        self.print("")
        self.print("  [bold #00ff00]n[/]  No  [#00aa00]— skip QC (faster, cheaper)[/]")
        self.print("")
        self.set_prompt(">  ")

    def _handle_options_input(self, value: str) -> None:
        """Handle quality control selection."""
        if value.lower() in ("n", "no"):
            self._no_qc = True
            self.print("[#00ff00]✓[/] Skipping QC")
        else:
            self._no_qc = False
            self.print("[#00ff00]✓[/] QC enabled")
        self.print("")
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
        elif self._stage == "model":
            self._handle_model_input(value)
        elif self._stage == "analyze_prompt":
            self._handle_analyze_prompt_input(value)
        elif self._stage == "transform":
            self._handle_transform_input(value)
        elif self._stage == "options":
            self._handle_options_input(value)
        elif self._stage == "export":
            self._handle_export_input(value)
        elif self._stage == "done":
            self._handle_done_input(value)

    def _handle_book_input(self, value: str) -> None:
        """Handle book selection."""
        sample = Path("books/texts/pride-prejudice-sample.txt")

        if value == "1":
            if sample.exists():
                self._select_book(sample)
            else:
                self.print("[#00ff00]Sample not found[/]")
        elif value == "2":
            self.print("[#00aa00]  Drag a .txt file into this window, or paste the full path[/]")
            self.set_prompt("path>  ")
        elif value.lower() in ("q", "quit"):
            self.exit()
        else:
            path = Path(value).expanduser()
            if path.exists() and path.is_file():
                self._select_book(path)
            elif path.exists():
                self.print("[#00ff00]That's a directory[/]")
            else:
                self.print("[#00ff00]File not found[/]")

    def _select_book(self, path: Path) -> None:
        """Select a book and show analysis."""
        self._selected_book = path
        self.book_title = self._get_book_title(path)
        self.print(f"[#00ff00]✓[/] {self.book_title}")

        # Analyze the book and update header
        stats = analyze_book_file(path)
        if stats:
            self._book_stats = stats
            # Update header metadata row
            with contextlib.suppress(Exception):
                self.query_one(HeaderBar).update_meta(stats)

        self.print("")
        self._show_model_menu()

    def _show_model_menu(self) -> None:
        """Kick off async model detection then render the selection menu."""
        from dotenv import load_dotenv

        load_dotenv()

        openai_key = os.environ.get("OPENAI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        has_openai = bool(openai_key and not openai_key.startswith("your-"))
        has_anthropic = bool(anthropic_key and not anthropic_key.startswith("your-"))

        if not has_openai and not has_anthropic:
            self.print("[#00ff00]⚠ No API keys configured — skipping model selection[/]")
            self._model_choices = []
            self._show_character_analysis_prompt()
            return

        self.print("[#00aa00]Detecting available models...[/]")
        self._fetch_and_show_models(has_openai, has_anthropic)

    @work(exclusive=True)
    async def _fetch_and_show_models(self, has_openai: bool, has_anthropic: bool) -> None:
        """Fetch live model lists from APIs, fall back to hardcoded list on error."""
        choices: list[tuple[str, str, str]] = []

        if has_anthropic:
            try:
                from anthropic import AsyncAnthropic

                client = AsyncAnthropic()
                page = await client.models.list(limit=50)
                for m in page.data:
                    if m.id.startswith("claude-"):
                        input_c, output_c = _lookup_model_cost(m.id)
                        pricing = f"${input_c:.2f} / ${output_c:.2f} per 1M tokens"
                        display = getattr(m, "display_name", m.id)
                        choices.append((m.id, display, pricing))
            except Exception:
                choices.extend(_FALLBACK_MODELS.get("anthropic", []))

        if has_openai:
            try:
                from openai import AsyncOpenAI

                client = AsyncOpenAI()
                models_page = await client.models.list()
                openai_models: list[tuple[str, str, str]] = []
                seen: set[str] = set()
                for m in sorted(models_page.data, key=lambda x: x.id):
                    if m.id in seen or not _should_show_openai_model(m.id):
                        continue
                    seen.add(m.id)
                    input_c, output_c = _lookup_model_cost(m.id)
                    pricing = f"${input_c:.2f} / ${output_c:.2f} per 1M tokens"
                    openai_models.append((m.id, _openai_display_name(m.id), pricing))
                choices.extend(
                    openai_models if openai_models else _FALLBACK_MODELS.get("openai", [])
                )
            except Exception:
                choices.extend(_FALLBACK_MODELS.get("openai", []))

        self._model_choices = choices
        self._render_model_menu()

    def _render_model_menu(self) -> None:
        """Display model selection menu after model list has been fetched."""
        if not self._model_choices:
            self._show_character_analysis_prompt()
            return

        if len(self._model_choices) == 1:
            model_id, display_name, _ = self._model_choices[0]
            os.environ["DEFAULT_MODEL"] = model_id
            self.print(f"[#00ff00]✓[/] Using [bold #00ff00]{display_name}[/]")
            self._recalculate_cost(model_id)
            self.print("")
            self._show_character_analysis_prompt()
            return

        self._stage = "model"
        current = _get_resolved_model()
        self.print("[#00ff00]?[/] [bold #00ff00]Select a model[/]")
        self.print("")
        for i, (model_id, display_name, pricing) in enumerate(self._model_choices, 1):
            marker = " [#00ff00]◄[/]" if model_id == current or current.startswith(model_id) else ""
            self.print(f"  [bold #00ff00]{i}[/]  {display_name:<22} [#00aa00]{pricing}[/]{marker}")
        self.print("")
        self.set_prompt(">  ")

    def _handle_model_input(self, value: str) -> None:
        """Handle model selection."""
        choices = getattr(self, "_model_choices", [])
        if not choices:
            self._show_character_analysis_prompt()
            return

        try:
            idx = int(value) - 1
            if 0 <= idx < len(choices):
                model_id, display_name, _ = choices[idx]
                os.environ["DEFAULT_MODEL"] = model_id
                self.print(f"[#00ff00]✓[/] {display_name}")
                self._recalculate_cost(model_id)
                self.print("")
                self._show_character_analysis_prompt()
                return
        except ValueError:
            pass

        for model_id, display_name, _ in choices:
            if value.lower() in (model_id.lower(), display_name.lower()):
                os.environ["DEFAULT_MODEL"] = model_id
                self.print(f"[#00ff00]✓[/] {display_name}")
                self._recalculate_cost(model_id)
                self.print("")
                self._show_character_analysis_prompt()
                return

        self.print(f"[#00ff00]Enter 1-{len(choices)}[/]")

    def _recalculate_cost(self, model: str) -> None:
        """Recalculate cost estimate for the selected model and update header."""
        if not self._book_stats:
            return
        tokens = self._book_stats.get("tokens", 0)
        input_cost, output_cost = _lookup_model_cost(model)
        estimated_cost = (tokens / 1_000_000 * input_cost) + (tokens / 1_000_000 * output_cost)
        self._book_stats["estimated_cost"] = estimated_cost
        self._book_stats["model"] = model
        with contextlib.suppress(Exception):
            self.query_one(HeaderBar).update_meta(self._book_stats)

    def _estimate_cost_str(self, token_fraction: float = 1.0) -> str:
        """Return a formatted cost estimate string for a fraction of the book's tokens."""
        if not self._book_stats:
            return ""
        tokens = self._book_stats.get("tokens", 0)
        model = os.environ.get("DEFAULT_MODEL", "")
        input_cost, output_cost = _lookup_model_cost(model)
        cost = tokens * token_fraction / 1_000_000 * (input_cost + output_cost)
        return f"~${cost:.2f}"

    def _show_character_analysis_prompt(self) -> None:
        """Ask if user wants to analyze characters first."""
        self._stage = "analyze_prompt"
        self.print("[#00ff00]?[/] [bold #00ff00]Analyze characters first?[/]")
        self.print("")
        cost = self._estimate_cost_str(0.2)
        cost_hint = f", costs {cost}" if cost else ""
        self.print(f"  [bold #00ff00]Y[/]  Yes [#00aa00](identifies characters{cost_hint})[/]")
        self.print("  [bold #00ff00]n[/]  No  [#00aa00](skip to transformation)[/]")
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
            with contextlib.suppress(Exception):
                self.query_one("#content", ContentArea).add_widget(self._analysis_loader)

            self._run_character_analysis()
        else:
            self.print("[#00ff00]✓[/] Skipped")
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

        Path("logs").mkdir(exist_ok=True)
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
                    if hasattr(self, "_analysis_loader"):
                        try:
                            self._analysis_loader.stop()
                            self._analysis_loader.remove()
                        except Exception:
                            pass
                    self.status_text = "Ready"

                    # Calculate elapsed time
                    elapsed = (
                        time.time() - self._analysis_start_time
                        if hasattr(self, "_analysis_start_time")
                        else 0
                    )

                    # Update header with character count
                    with contextlib.suppress(Exception):
                        self.query_one(HeaderBar).update_meta(self._book_stats, char_count)

                    self.print(
                        f"[#00ff00]✓[/] Found [bold #00ff00]{char_count}[/] characters [#00aa00]({elapsed:.1f}s)[/]"
                    )

                    # Show gender breakdown
                    gender_parts = []
                    for gender, count in by_gender.items():
                        gender_parts.append(f"{count} {gender}")
                    if gender_parts:
                        self.print(f"  [#00aa00]Genders:[/] {', '.join(gender_parts)}")

                    # Show top characters
                    if main_chars:
                        self.print("")
                        self.print("  [#00aa00]Main characters:[/]")
                        for name in main_chars[:5]:
                            self.print(f"    [#00ff00]•[/] {name}")
                        if len(main_chars) > 5:
                            self.print(f"    [#00aa00]... and {len(main_chars) - 5} more[/]")

                    self.print("")
                    self._show_transform_menu()

                show_results()
            else:
                error_msg = result.get("error", "Unknown error")
                debug_log.error(f"Analysis returned failure: {error_msg}")
                # Stop braille loader
                self._analysis_running = False
                if hasattr(self, "_analysis_loader"):
                    try:
                        self._analysis_loader.stop()
                        self._analysis_loader.remove()
                    except Exception:
                        pass
                self.status_text = "Ready"

                self.print(f"\n[#00ff00]Analysis failed:[/] {error_msg}")
                self.print("[#00aa00]  See logs/tui_debug.log for details[/]")
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
            if hasattr(self, "_analysis_loader"):
                try:
                    self._analysis_loader.stop()
                    self._analysis_loader.remove()
                except Exception:
                    pass
            self.status_text = "Ready"

            self.print(f"\n[#00ff00]Error:[/] {error_msg}")
            self.print("[#00aa00]  See logs/tui_debug.log for full traceback[/]")
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
                "[#00aa00]Add your API keys to[/] [bold #00ff00].env[/] [#00aa00]in the project folder:[/]"
            )
            self.print("[#00aa00]  OPENAI_API_KEY=sk-...[/]")
            self.print("[#00aa00]  DEFAULT_PROVIDER=openai[/]")
            self.print("[#00aa00]Then restart the app.[/]")

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
                self.print(f"[#00ff00]✓[/] {self._selected_transform}")
                self.print("")
                self._show_options_menu()
                return
        except ValueError:
            for name, _ in self.TRANSFORM_TYPES:
                if value.lower() == name.lower():
                    self._selected_transform = name
                    self.transform_type = name
                    self.print(f"[#00ff00]✓[/] {name}")
                    self.print("")
                    self._show_options_menu()
                    return

        self.print(f"[#00ff00]Enter 1-{len(self.TRANSFORM_TYPES)}[/]")

    # -------------------------------------------------------------------------
    # Processing
    # -------------------------------------------------------------------------

    def _show_stage_loader(self, stage_name: str, start_time: float) -> None:
        """Show braille loader for a stage."""

        def show_loader():
            # Stop any existing loader
            if hasattr(self, "_stage_loader") and self._stage_loader:
                try:
                    self._stage_loader.stop()
                    self._stage_loader.remove()
                except Exception:
                    pass

            # Show new braille loader
            self._stage_loader = BrailleLoader(stage_name, start_time)
            with contextlib.suppress(Exception):
                self.query_one("#content", ContentArea).add_widget(self._stage_loader)

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

        self.print(f"{gradient_text('Starting transformation', ['#00ff00', '#00aa00'])}...")

        # Show braille loader with elapsed timer
        self._transform_loader = BrailleLoader("Transforming", self._process_start)
        with contextlib.suppress(Exception):
            self.query_one("#content", ContentArea).add_widget(self._transform_loader)

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
            Path("logs").mkdir(exist_ok=True)
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

            transform_type = self._result.get("transform_type")

            # Route special transform types to dedicated app methods
            if transform_type == "parse_only":
                debug_log.info("Calling parse_book (await)...")
                result = await app.parse_book(
                    file_path=self._result["input"],
                    output_path=self._result.get("output_path"),
                )
                debug_log.info(f"parse_book returned: success={result.get('success')}")
                app.shutdown()
                debug_log.info("App shutdown OK")
                self._show_complete(result)
                return

            if transform_type == "character_analysis":
                debug_log.info("Calling analyze_characters (await)...")
                result = await app.analyze_characters(
                    file_path=self._result["input"],
                    output_path=self._result.get("output_path"),
                )
                debug_log.info(f"analyze_characters returned: success={result.get('success')}")
                app.shutdown()
                debug_log.info("App shutdown OK")
                self._show_complete(result)
                return

            debug_log.info("Calling process_book (await)...")
            result = await app.process_book(
                file_path=self._result["input"],
                transform_type=transform_type,
                output_path=self._result.get("output_path"),
                quality_control=not self._result.get("no_qc", True),
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
        if hasattr(self, "_stage_loader") and self._stage_loader:
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
                    eta_str = f" [#00aa00]~{int(remaining)}s left[/]"
                else:
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    eta_str = f" [#00aa00]~{mins}m {secs}s left[/]"

        # Build gradient progress bar (green)
        bar_width = 50
        filled = int(bar_width * pct)
        empty = bar_width - filled

        # Gradient colors for filled portion
        gradient_colors = [
            "#00ff00",
            "#00dd00",
            "#00bb00",
            "#009900",
            "#007700",
            "#005500",
        ]
        filled_chars = []
        for i in range(filled):
            progress_in_fill = i / max(1, filled - 1) if filled > 1 else 0
            color_idx = int(progress_in_fill * (len(gradient_colors) - 1))
            color = gradient_colors[color_idx]
            filled_chars.append(f"[{color}]━[/]")

        filled_str = "".join(filled_chars)
        empty_str = f"[#00ff00]{'━' * empty}[/]"
        bar = filled_str + empty_str

        # Percentage color
        pct_color = "#00ff00"

        # Stage name with green gradient
        stage_gradient = gradient_text(stage_name, ["#00ff00", "#00aa00"])

        def update():
            self.status_text = f"{stage_name} {pct_int}%"
            # Update progress line in place
            progress_line = f"  {stage_gradient:<25} {bar} [{pct_color}]{pct_int:>3}%[/]{eta_str}"
            with contextlib.suppress(Exception):
                self.query_one("#content", ContentArea).update_progress(progress_line)

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
            if hasattr(self, "_stage_loader") and self._stage_loader:
                try:
                    self._stage_loader.stop()
                    self._stage_loader.remove()
                    self._stage_loader = None
                except Exception:
                    pass

            # Clear the in-place progress line
            with contextlib.suppress(Exception):
                self.query_one("#content", ContentArea).clear_progress()

            # Add completion message with gradient
            stage_gradient = gradient_text(stage_name, ["#00ff00", "#00aa00"])
            msg = f"[#00ff00]✓[/] {stage_gradient} [#00aa00]({event.elapsed_seconds:.1f}s)[/]"
            if stats:
                msg += f" [#00aa00]— {stats}[/]"
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
            self.print("[#00ff00]⚠ Transformation completed but output file not found[/]")
            self.print(f"  [#00aa00]Expected:[/] {output_path}")
            self.print(f"  [#00aa00]Time:[/] {elapsed:.1f}s (suspicious if < 5s)")
            self.print("")
            self._json_output_path = None
            self._show_final()
            return

        # Stop transform loader
        if hasattr(self, "_transform_loader") and self._transform_loader:
            try:
                self._transform_loader.stop()
                self._transform_loader.remove()
                self._transform_loader = None
            except Exception:
                pass

        transform = self._selected_transform or ""
        if transform == "parse_only":
            label = "Parsing complete!"
        elif transform == "character_analysis":
            label = "Character analysis complete!"
        else:
            label = "Transformation complete!"
        self.print("")
        self.print(f"[#00ff00]✓[/] {gradient_text(label, ['#00ff00', '#00aa00'])}")
        self.print(f"  [#00aa00]Time:[/] [#00ff00]{elapsed:.1f}s[/]")
        self.print(f"  [#00aa00]Saved:[/] [#00ff00]{self._json_output_path}[/]")
        qc_score = result.get("quality_score")
        qc_corrections = result.get("qc_corrections")
        if qc_score is not None:
            self.print(
                f"  [#00aa00]QC score:[/] [#00ff00]{qc_score}%[/] [#00aa00]({qc_corrections} corrections)[/]"
            )

        # Show export options from FORMATS
        self._stage = "export"
        self._export_format_list = list(FORMATS.keys())
        self.print("")
        self.print("[#00ff00]?[/] [bold #00ff00]Export format[/]")
        self.print("")
        for i, key in enumerate(self._export_format_list, 1):
            info = FORMATS[key]
            self.print(f"  [bold #00ff00]{i}[/]  {key:<15} [#00aa00]{info['description']}[/]")
        skip_num = len(self._export_format_list) + 1
        self.print(f"  [bold #00ff00]{skip_num}[/]  skip [#00aa00](JSON only)[/]")
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
            self.print("[#00ff00]✓[/] Skipped export")
            self._show_final()
            return

        format_map = {str(i): k for i, k in enumerate(format_list, 1)}
        format_map.update({k: k for k in format_list})
        format_map["text"] = "txt"
        format_key = format_map.get(value.lower() if value else "")
        if not format_key:
            self.print(f"[#00ff00]Enter 1-{skip_num} or format key[/]")
            return

        if not self._json_output_path:
            self.print(
                "[#00ff00]⚠[/] [#00aa00]No JSON output path available. Transformation may have saved to a different location.[/]"
            )
            self._show_final()
            return

        # Do the export
        try:
            from pathlib import Path

            json_path = Path(self._json_output_path)
            output_path = export_book(str(json_path), format_key)
            self.print(f"[#00ff00]✓[/] Exported to [#00ff00]{output_path}[/]")
        except Exception as e:
            self.print(f"[#00ff00]Export error:[/] {e}")

        self._show_final()

    def _show_final(self) -> None:
        """Offer to transform another book or quit."""
        self._stage = "done"
        self.print("")
        self.print("[#00ff00]?[/] [bold #00ff00]What next?[/]")
        self.print("")
        self.print("  [bold #00ff00]1[/]  Transform another book")
        self.print("  [bold #00ff00]2[/]  Quit")
        self.print("")
        self.status_text = "Complete ✓"

        try:
            input_bar = self.query_one(InputBar)
            input_bar.stop_loading_animation(restore="[#00ff00]✓[/]  ")
            input_bar.enable()
        except Exception:
            pass

    def _handle_done_input(self, value: str) -> None:
        """Handle post-completion menu: restart or quit."""
        if value in ("1", "again", "a", "y", "yes"):
            self._restart_flow()
        elif value in ("2", "q", "quit", "exit", ""):
            self.exit()
        else:
            self.print("[#00ff00]Enter 1 or 2[/]")

    def _restart_flow(self) -> None:
        """Reset state and start a new transformation."""
        self._selected_book = None
        self._selected_transform = None
        self._no_qc = False
        self._result = None
        self._process_start = None
        self._json_output_path = None
        self._output_path = None
        self._stage_start = None
        self._current_stage = None
        self._last_progress_line_id = None
        self._book_stats = None
        self._analysis_running = False
        self._transform_loader = None
        self._stage_loader = None
        self._analysis_loader = None
        self._model_choices = []
        os.environ.pop("DEFAULT_MODEL", None)

        self.book_title = "—"
        self.transform_type = "—"
        self.status_text = "Ready"

        self.print("")
        self.print("[#00ff00]─[/]" * 50)
        self.print("")
        self._show_book_menu()

    def _show_error(self, error: str) -> None:
        """Show error and offer to try again or quit."""
        # Stop any active loaders
        for attr in ("_transform_loader", "_stage_loader", "_analysis_loader"):
            loader = getattr(self, attr, None)
            if loader:
                try:
                    loader.stop()
                    loader.remove()
                except Exception:
                    pass
                setattr(self, attr, None)

        self.print("")
        self.print(f"[bold #00ff00]✗ Error:[/bold #00ff00] {error}")
        self.print("")
        self.status_text = "Error"

        self._stage = "done"
        self.print("[#00ff00]?[/] [bold #00ff00]What next?[/]")
        self.print("")
        self.print("  [bold #00ff00]1[/]  Try another book")
        self.print("  [bold #00ff00]2[/]  Quit")
        self.print("")
        try:
            input_bar = self.query_one(InputBar)
            input_bar.stop_loading_animation(restore="[#00ff00]✗[/]  ")
            input_bar.enable()
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
