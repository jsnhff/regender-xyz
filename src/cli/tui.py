"""
Textual TUI for Regender

A polished terminal user interface with fixed header, scrollable content,
and input footer.
"""

from __future__ import annotations

import contextlib
import math
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import DirectoryTree, Input, Label, Static

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
    "#ffffff",
    "#ff0080",
    "#ff1a8c",
    "#ff3399",
    "#ff4da6",
    "#ff66b3",
    "#ff80c0",
    "#ff99cc",
]
CYAN_BLUE = ["#ffffff", "#00d4ff", "#00b3ff", "#0099ff", "#007fff", "#0066ff", "#004dff", "#0033ff"]
YELLOW_ORANGE = [
    "#ffffff",
    "#ffb00a",
    "#ffa209",
    "#ff9408",
    "#ff8607",
    "#ff7806",
    "#ff6a05",
    "#ff5c04",
]
VIOLET_MAGENTA = [
    "#ffffff",
    "#9033e8",
    "#9d2ee4",
    "#aa29e0",
    "#b724dc",
    "#c41fd8",
    "#d11ad4",
    "#de15d0",
]
PINK_VIOLET = [
    "#ffffff",
    "#f01a82",
    "#e13396",
    "#d24daa",
    "#c366be",
    "#b480d2",
    "#a599e6",
    "#96b3fa",
]
FIRE_GLOW = ["#ffffff", "#ff3355", "#ff5c3d", "#ff8526", "#ffae0f"]


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


def _format_model_name(model: str) -> str:
    """Shorten model IDs for display: claude-opus-4-5-20251101 → claude opus 4.5"""
    import re

    m = re.match(r"claude-(opus|sonnet|haiku)-(\d+)-(\d+)", model)
    if m:
        return f"claude {m.group(1)} {m.group(2)}.{m.group(3)}"
    return model


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


def _lookup_model_cost(model: str) -> tuple[float, float] | None:
    """Match model string to cost table. Returns None if model is unrecognized."""
    if model in MODEL_COSTS:
        return MODEL_COSTS[model]
    for key in MODEL_COSTS:
        if model.startswith(key):
            return MODEL_COSTS[key]
    return None


# Recommended model IDs — best quality/cost balance for literary transforms
_RECOMMENDED_MODELS = ("claude-sonnet-4-6", "claude-sonnet-4", "gpt-4o")


def _is_recommended_model(model_id: str) -> bool:
    """Return True if this model is our recommended choice for transforms."""
    return any(model_id.startswith(prefix) for prefix in _RECOMMENDED_MODELS)


_MODEL_SECS_PER_1K_TOKENS: dict[str, float] = {
    "claude-haiku": 6.0,
    "claude-sonnet": 12.0,
    "claude-opus": 28.0,
    "gpt-4o-mini": 7.0,
    "gpt-4o": 13.0,
    "gpt-4-turbo": 20.0,
    "gpt-4": 22.0,
    "gpt-3.5-turbo": 5.0,
}


def _estimate_transform_time(model_id: str, tokens: int) -> str:
    """Return a human-readable time estimate for transforming `tokens` book tokens."""
    if tokens <= 0:
        return ""
    secs_per_1k = 6.0
    for prefix, rate in _MODEL_SECS_PER_1K_TOKENS.items():
        if model_id.startswith(prefix):
            secs_per_1k = rate
            break
    total_secs = tokens / 1000 * secs_per_1k
    if total_secs < 90:
        return f"~{int(total_secs)}s"
    minutes = total_secs / 60
    return "~1 min" if minutes < 2 else f"~{int(minutes)} min"


_FALLBACK_MODELS: dict[str, list[tuple[str, str, str]]] = {
    "anthropic": [
        ("claude-sonnet-4-6", "Claude Sonnet 4.6", "$3 / $15 per 1M tokens"),
        ("claude-opus-4-6", "Claude Opus 4.6", "$15 / $75 per 1M tokens"),
        ("claude-haiku-4-5-20251001", "Claude Haiku 4.5", "$0.80 / $4 per 1M tokens"),
    ],
    "openai": [
        ("gpt-4o", "GPT-4o", "$2.50 / $10 per 1M tokens"),
        ("gpt-4o-mini", "GPT-4o Mini", "$0.15 / $0.60 per 1M tokens"),
    ],
}

_OPENAI_SHOW_PREFIXES = ("gpt-4", "gpt-3.5-turbo", "o1", "o3", "o4")
_OPENAI_SKIP_PATTERNS = (
    "instruct", "realtime", "audio", "tts", "whisper", "dall-e", "embedding", "search",
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
    name = model_id
    for prefix, replacement in (("gpt-", "GPT-"), ("o1", "O1"), ("o3", "O3"), ("o4", "O4")):
        if name.startswith(prefix):
            name = replacement + name[len(prefix):]
            break
    return name.replace("-", " ")


def _version_from_model_id(model_id: str) -> str:
    """Extract semantic version string from a model ID, e.g. 'claude-sonnet-4-6' → '4.6'."""
    m = re.search(r"-(\d+)-(\d+)(?:-\d+)?$", model_id)
    return f"{m.group(1)}.{m.group(2)}" if m else ""


def _friendly_model_name(model: str) -> str:
    """Convert API model ID to a short display name."""
    all_models = [m for models in _FALLBACK_MODELS.values() for m in models]
    for model_id, display_name, _ in all_models:
        if model == model_id:
            return display_name
    for model_id, display_name, _ in sorted(all_models, key=lambda m: -len(m[0])):
        if model.startswith(model_id):
            return display_name
    return _format_model_name(model)


def _versioned_display_name(model_id: str, api_display: str) -> str:
    """Ensure the display name includes the version number from the model ID."""
    version = _version_from_model_id(model_id)
    if version and version not in api_display:
        return f"{api_display} {version}"
    return api_display


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
    costs = _lookup_model_cost(model)

    # Input = book text + prompts, output ~ same size as book
    estimated_cost = (
        (tokens / 1_000_000 * costs[0]) + (tokens / 1_000_000 * costs[1]) if costs else None
    )

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
$primary: #ffffff;        /* Hot magenta */
$secondary: #ffffff;      /* Electric cyan */
$accent: #ffffff;         /* Bold yellow */
$violet: #ffffff;         /* Deep violet */
$background: #000000;     /* Black */
$surface: #000000;        /* Black */
$text: #ffffff;           /* Green */
$text-dim: #aaaaaa;       /* Lavender dim */
$success: #ffffff;        /* Cyan */
$error: #ffffff;          /* Magenta */
"""


# =============================================================================
# Widgets
# =============================================================================


# Green gradient palette for header
GREEN_GRADIENT = ["#ffffff", "#dddddd", "#bbbbbb", "#aaaaaa", "#888888"]

# Logo - green gradient on black
LOGO_ART = gradient_text("regender", GREEN_GRADIENT) + gradient_text(".xyz", ["#aaaaaa", "#ffffff"])


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
            wave_colors = ["#ffffff", "#dddddd", "#bbbbbb", "#999999", "#777777", "#555555"]

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
            msg = gradient_text(self._message, ["#ffffff", "#aaaaaa"])

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
        border-bottom: heavy #ffffff;
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
        color: #ffffff;
    }

    HeaderBar #stats-row1 > Label, HeaderBar #stats-row2 > Label {
        width: 1fr;
    }

    HeaderBar #stats-row1 > Label:first-child,
    HeaderBar #stats-row2 > Label:first-child {
        width: 2fr;
    }

    HeaderBar #stats-row2 > Label#model-label {
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
            yield Label(gradient_text("v1.0", ["#aaaaaa", "#ffffff"]), id="version")

        # Border (wide enough for large terminals)
        yield Label("─" * 200, id="border1")

        # Row 1: book stats
        with Horizontal(id="stats-row1"):
            yield Label(f"[#aaaaaa]book:[/] [#ffffff]{self._book}[/]")
            yield Label(f"[#aaaaaa]pages:[/] [#ffffff]{self._pages}[/]")
            yield Label(f"[#aaaaaa]chapters:[/] [#ffffff]{self._chapters}[/]")
            yield Label(f"[#aaaaaa]characters:[/] [#ffffff]{self._characters}[/]")

        # Border (wide enough for large terminals)
        yield Label("─" * 200, id="border2")

        # Row 2: processing info
        with Horizontal(id="stats-row2"):
            yield Label(f"[#aaaaaa]transformation:[/] [#ffffff]{self._transform}[/]")
            yield Label(f"[#aaaaaa]model:[/] [#ffffff]{self._model}[/]", id="model-label")
            yield Label(f"[#aaaaaa]total cost:[/] [#ffffff]{self._cost}[/]")

    def update_status(self, book: str = None, transform: str = None, status: str = None) -> None:
        """Update book and transform fields."""
        if book is not None:
            self._book = book
        if transform is not None:
            self._transform = transform
        self._refresh()

    def update_meta(self, stats: dict | None, char_count: int | None = None) -> None:
        """Update all metadata fields."""
        if stats:
            self._pages = str(stats.get("pages", "—"))
            self._chapters = str(stats.get("chapters", "—"))
            self._cost = f"${stats.get('estimated_cost', 0):.2f}"
            self._model = _format_model_name(stats.get("model", "—"))

        if char_count is not None:
            self._characters = str(char_count)

        self._refresh()

    def _refresh(self) -> None:
        """Update all labels with current values."""
        try:
            labels = self.query("#stats-row1 > Label")
            if len(labels) >= 4:
                labels[0].update(Text.from_markup(f"[#aaaaaa]book:[/] [#ffffff]{self._book}[/]"))
                labels[1].update(Text.from_markup(f"[#aaaaaa]pages:[/] [#ffffff]{self._pages}[/]"))
                labels[2].update(
                    Text.from_markup(f"[#aaaaaa]chapters:[/] [#ffffff]{self._chapters}[/]")
                )
                labels[3].update(
                    Text.from_markup(f"[#aaaaaa]characters:[/] [#ffffff]{self._characters}[/]")
                )

            labels = self.query("#stats-row2 > Label")
            if len(labels) >= 3:
                labels[0].update(
                    Text.from_markup(f"[#aaaaaa]transformation:[/] [#ffffff]{self._transform}[/]")
                )
                labels[1].update(Text.from_markup(f"[#aaaaaa]model:[/] [#ffffff]{self._model}[/]"))
                labels[2].update(
                    Text.from_markup(f"[#aaaaaa]total cost:[/] [#ffffff]{self._cost}[/]")
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
        scrollbar-background: #000000;
        scrollbar-background-hover: #000000;
        scrollbar-background-active: #000000;
        scrollbar-color: #333333;
        scrollbar-color-hover: #ffffff;
        scrollbar-color-active: #ffffff;
        scrollbar-size: 1 1;
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

    _progress_label: Label | None = None

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
            msg = f"[#ffffff]{frame_char}[/] [#aaaaaa]{self._activity}[/] [#ffffff]({time_str})[/]"
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
        border-top: heavy #ffffff;
        padding: 0 1;
    }

    InputBar > Horizontal {
        height: 100%;
        align: left middle;
    }

    InputBar #prompt {
        width: auto;
        color: #ffffff;
    }

    InputBar #input {
        width: 1fr;
        border: none;
        background: #000000;
        color: #ffffff;
        padding: 0;
    }

    InputBar #input:focus {
        border: none;
        color: #ffffff;
    }

    InputBar #input.-disabled {
        color: #aaaaaa;
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
            self.set_prompt(f"[#ffffff]{frame}[/] ")
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
        border-top: solid #ffffff;
        padding: 0 2;
        color: #ffffff;
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


class _TxtDirectoryTree(DirectoryTree):
    """DirectoryTree that shows only directories and .txt files."""

    def filter_paths(self, paths):
        return [p for p in paths if p.is_dir() or p.suffix == ".txt"]


class FileBrowserScreen(Screen):
    """Full-screen file browser for selecting a book file."""

    DEFAULT_CSS = """
    FileBrowserScreen {
        background: #000000;
        padding: 0;
    }
    FileBrowserScreen Label {
        color: #aaaaaa;
        padding: 0 1;
    }
    FileBrowserScreen _TxtDirectoryTree {
        background: #000000;
        color: #ffffff;
        height: 1fr;
        border: solid #aaaaaa;
    }
    FileBrowserScreen _TxtDirectoryTree > .tree--cursor {
        background: #333333;
        color: #ffffff;
    }
    FileBrowserScreen _TxtDirectoryTree:focus > .tree--cursor {
        background: #555555;
        color: #ffffff;
    }
    """

    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
        ("enter", "select", "Select"),
    ]

    def __init__(self, start_path: Path, **kwargs):
        super().__init__(**kwargs)
        self._start_path = start_path

    def compose(self) -> ComposeResult:
        yield Label("Browse — arrows to navigate, Enter to select, Esc to cancel  (.txt files only)")
        yield _TxtDirectoryTree(str(self._start_path))

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        self.dismiss(Path(event.path))

    def action_select(self) -> None:
        tree = self.query_one(_TxtDirectoryTree)
        node = tree.cursor_node
        if node and node.data and node.data.path:
            path = Path(node.data.path)
            if path.is_file():
                self.dismiss(path)


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

    def __init__(self, process_callback: Callable | None = None, **kwargs):
        super().__init__(**kwargs)
        self._process_callback = process_callback
        self._stage = "book"  # book, transform, options, name_map, processing, done
        self._selected_book: Path | None = None
        self._selected_transform: str | None = None
        self._no_qc = False
        self._name_map: dict[str, str] | None = None
        self._pending_characters = None
        self._name_suggestions: list[dict] = []
        self._name_review_idx: int = 0
        self._name_edit_mode: bool = False
        self._name_custom_mode: bool = False
        self._custom_title: str = ""
        self._model_choices: list = []
        self._model_showing_all: bool = False
        self._result: dict | None = None
        self._process_start: float | None = None
        self._json_output_path: str | None = None
        self._output_path: Path | None = None
        self._stage_start: float | None = None
        self._current_stage: str | None = None
        self._last_progress_line_id: str | None = None
        self._book_stats: dict | None = None
        self._analysis_running: bool = False

    def compose(self) -> ComposeResult:
        yield HeaderBar(id="header")
        yield ContentArea(id="content")
        yield InputBar()

    def on_mount(self) -> None:
        """Initialize the app."""
        self._update_header()

        # Simple welcome message
        self.print("[#ffffff]◆[/] [#aaaaaa]Welcome to regender.xyz[/]")
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
            self.print("[bold #ffffff]⚠ No API keys detected[/]")
            self.print("")
            self.print(
                "[#aaaaaa]Add these to[/] [bold #ffffff].env[/] [#aaaaaa]in the project folder:[/]"
            )
            self.print("")
            self.print("  [#ffffff]# For OpenAI:[/]")
            self.print("  [#ffffff]OPENAI_API_KEY=sk-...[/]")
            self.print("  [#ffffff]DEFAULT_PROVIDER=openai[/]")
            self.print("")
            self.print("  [#ffffff]# Or for Anthropic:[/]")
            self.print("  [#ffffff]ANTHROPIC_API_KEY=sk-ant-...[/]")
            self.print("  [#ffffff]DEFAULT_PROVIDER=anthropic[/]")
            self.print("")
            self.print(
                "[#aaaaaa]Then restart the app. You can still use 'parse_only' without keys.[/]"
            )
            self.print("")
        elif not provider:
            # Has keys but no provider set
            available = []
            if has_openai:
                available.append("openai")
            if has_anthropic:
                available.append("anthropic")
            self.print("[bold #ffffff]⚠ DEFAULT_PROVIDER not set[/]")
            self.print("")
            self.print(f"[#aaaaaa]You have API keys for: {', '.join(available)}[/]")
            self.print(
                "[#aaaaaa]Add this to[/] [bold #ffffff].env[/] [#aaaaaa]in the project folder:[/]"
            )
            self.print(f"  [#ffffff]DEFAULT_PROVIDER={available[0]}[/]")
            self.print("")
        else:
            # All good - show which provider is active
            self.print(f"[#ffffff]◆[/] [#aaaaaa]Using {provider} for LLM calls[/]")
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
        self.print("[#ffffff]?[/] [bold #ffffff]Select a book[/]")
        self.print("")
        self.print(
            "  [#aaaaaa]Add plain-text (.txt) books to [bold]books/texts/[/] in this folder[/]"
        )
        self.print(
            "  [#aaaaaa]then choose an option below.[/]"
        )
        self.print("")
        self.print("  [bold #ffffff]1[/]  Browse files in [bold]books/texts/[/]...")
        self.print("  [bold #ffffff]2[/]  Enter or drag file path...")
        self.print("  [bold #ffffff]3[/]  Pride and Prejudice [#aaaaaa](sample)[/]")
        self.print("")
        self.set_prompt(">  ")

    def _show_transform_menu(self) -> None:
        """Show transform selection with colorful styling."""
        self._stage = "transform"
        self.print("[#ffffff]?[/] [bold #ffffff]Select transformation[/]")
        self.print("")
        for i, (name, desc) in enumerate(self.TRANSFORM_TYPES, 1):
            self.print(f"  [bold #ffffff]{i}[/]  {name:<18} [#aaaaaa]{desc}[/]")
        self.print("")
        self.set_prompt(">  ")

    def _show_options_menu(self) -> None:
        """Show options with colorful styling."""
        # Calculate and show output path
        self._calculate_output_path()
        self.print("")
        self.print("[#aaaaaa]Output will be saved to:[/]")
        self.print(f"  [#ffffff]{self._output_path}[/]")
        self.print("")
        self._show_retitle_prompt()

    # Gendered words likely to appear in book titles, by transform type
    _TITLE_WORD_SWAPS: dict[str, dict[str, str]] = {
        "all_male": {
            "women": "men", "woman": "man", "girl": "boy", "girls": "boys",
            "lady": "lord", "ladies": "lords", "queen": "king", "queens": "kings",
            "mother": "father", "mothers": "fathers", "sister": "brother", "sisters": "brothers",
            "daughter": "son", "daughters": "sons", "wife": "husband", "wives": "husbands",
            "widow": "widower", "widows": "widowers", "nun": "monk", "nuns": "monks",
            "princess": "prince", "duchess": "duke", "empress": "emperor",
        },
        "all_female": {
            "men": "women", "man": "woman", "boy": "girl", "boys": "girls",
            "lord": "lady", "lords": "ladies", "king": "queen", "kings": "queens",
            "father": "mother", "fathers": "mothers", "brother": "sister", "brothers": "sisters",
            "son": "daughter", "sons": "daughters", "husband": "wife", "husbands": "wives",
            "widower": "widow", "widowers": "widows", "monk": "nun", "monks": "nuns",
            "prince": "princess", "duke": "duchess", "emperor": "empress",
        },
        "gender_swap": {
            "women": "men", "men": "women", "woman": "man", "man": "woman",
            "girl": "boy", "boy": "girl", "girls": "boys", "boys": "girls",
            "lady": "lord", "lord": "lady", "queen": "king", "king": "queen",
            "sister": "brother", "brother": "sister",
            "daughter": "son", "son": "daughter",
            "wife": "husband", "husband": "wife",
            "princess": "prince", "prince": "princess",
        },
        "nonbinary": {
            "women": "people", "woman": "person", "men": "people", "man": "person",
            "girl": "youth", "girls": "youth", "boy": "youth", "boys": "youth",
            "sister": "sibling", "brother": "sibling",
            "queen": "monarch", "king": "monarch",
            "lady": "noble", "lord": "noble",
        },
    }

    def _suggest_title(self, title: str, transform_type: str) -> str:
        """Return a gendered-word-swapped version of title, or the original if nothing changes."""
        swaps = self._TITLE_WORD_SWAPS.get(transform_type, {})
        result = title
        for old, new in swaps.items():
            pattern = re.compile(r"\b" + re.escape(old) + r"\b", re.IGNORECASE)
            def _replace(m, _new=new):
                w = m.group(0)
                if w.isupper():
                    return _new.upper()
                if w[0].isupper():
                    return _new.capitalize()
                return _new
            result = pattern.sub(_replace, result)
        return result

    def _show_retitle_prompt(self) -> None:
        """Ask if user wants a custom title for the output."""
        self._stage = "retitle"
        current = self._custom_title or self.book_title
        suggested = self._suggest_title(current, self._selected_transform or "")
        self._suggested_title = suggested if suggested != current else ""

        self.print("[#ffffff]?[/] [bold #ffffff]Title for output book[/]")
        self.print(f"  [#aaaaaa]Current: {current}[/]")
        if self._suggested_title:
            self.print(f"  [bold #ffffff]Suggested:[/] {self._suggested_title}")
            self.print("")
            self.print("  [bold #ffffff]S[/]  Use suggested title")
            self.print("  [bold #ffffff]↵[/]  Keep current")
            self.print("  [#aaaaaa]or type a new title[/]")
        else:
            self.print("")
            self.print("  Type a new title, or press [bold #ffffff]Enter[/] to keep it")
        self.print("")
        self.set_prompt(">  ")

    def _handle_retitle_input(self, value: str) -> None:
        """Handle retitle prompt input."""
        suggested = getattr(self, "_suggested_title", "")
        if value.strip().lower() == "s" and suggested:
            self._custom_title = suggested
            self.print(f"[#ffffff]✓[/] Title set to: [bold #ffffff]{self._custom_title}[/]")
        elif value.strip():
            self._custom_title = value.strip()
            self.print(f"[#ffffff]✓[/] Title set to: [bold #ffffff]{self._custom_title}[/]")
        else:
            self.print(f"[#ffffff]✓[/] Keeping: [bold #ffffff]{self._custom_title or self.book_title}[/]")
        self.print("")
        self._no_qc = True
        self._run_name_review()

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
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
            self._output_path = output_dir / f"characters_{ts}.json"
        else:
            # For transformations: save to book's output folder with transformation type + timestamp
            output_dir = Path("books/output") / book_folder
            output_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
            self._output_path = output_dir / f"{self._selected_transform}_{ts}.json"

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
        elif self._stage == "model":
            self._handle_model_input(value)
        elif self._stage == "options":
            self._handle_options_input(value)
        elif self._stage == "retitle":
            self._handle_retitle_input(value)
        elif self._stage == "name_review":
            self._handle_name_review_input(value)
        elif self._stage == "export":
            self._handle_export_input(value)
        elif self._stage == "done":
            self._handle_done_input(value)

    def _handle_book_input(self, value: str) -> None:
        """Handle book selection."""
        sample = Path("books/texts/pride-prejudice-sample.txt")

        if value == "1":
            start = Path("books/texts") if Path("books/texts").exists() else Path.home()
            self.push_screen(FileBrowserScreen(start), self._on_file_browser_result)
        elif value == "2":
            self.print("[#aaaaaa]  Drag a .txt file into this window, or paste the full path[/]")
            self.set_prompt("path>  ")
        elif value == "3":
            if sample.exists():
                self._select_book(sample)
            else:
                self.print("[#ffffff]Sample not found — add pride-prejudice-sample.txt to books/texts/[/]")
        elif value.lower() == "regender me":
            self._easter_egg()
        elif value.lower() in ("q", "quit"):
            self.exit()
        else:
            path = Path(value).expanduser()
            if path.exists() and path.is_file():
                self._select_book(path)
            elif path.exists():
                self.print("[#ffffff]That's a directory[/]")
            else:
                self.print("[#ffffff]File not found[/]")

    def _easter_egg(self) -> None:
        """Regender the regendering tool."""
        lines = [
            "",
            gradient_text("regendering the regendering tool...", GREEN_GRADIENT),
            "",
            "  [#aaaaaa]Original:[/]  [#ffffff]She transforms gender representation in literature using AI.[/]",
            "  [#aaaaaa]Regendered:[/] [#ffffff]He transforms gender representation in literature using AI.[/]",
            "  [#aaaaaa]Regendered:[/] [#ffffff]They transform gender representation in literature using AI.[/]",
            "  [#aaaaaa]Regendered:[/] [#ffffff]It transforms gender representation in literature using AI.[/]",
            "",
            "  [#aaaaaa]✓ regendered in 0.000s · quality score 100%[/]",
            "",
        ]
        for line in lines:
            self.print(line)

    def _on_file_browser_result(self, path: Path | None) -> None:
        """Called when the file browser screen is dismissed."""
        if path is None:
            return  # user pressed Esc
        if path.is_file():
            self._select_book(path)
        else:
            self.print("[#ffffff]No file selected[/]")

    def _select_book(self, path: Path) -> None:
        """Select a book and show analysis."""
        self._selected_book = path
        self.book_title = self._get_book_title(path)
        self.print(f"[#ffffff]✓[/] {self.book_title}")

        # Analyze the book and update header
        stats = analyze_book_file(path)
        if stats:
            self._book_stats = stats
            # Update header metadata row
            with contextlib.suppress(Exception):
                self.query_one(HeaderBar).update_meta(stats)

        self.print("")
        self._show_model_menu()

    def _estimate_cost_str(self, token_fraction: float = 1.0) -> str:
        """Return a formatted cost estimate string for a fraction of the book's tokens."""
        if not self._book_stats:
            return ""
        tokens = self._book_stats.get("tokens", 0)
        model = os.environ.get("DEFAULT_MODEL", "")
        costs = _lookup_model_cost(model)
        if not costs:
            return ""
        cost = tokens * token_fraction / 1_000_000 * (costs[0] + costs[1])
        return f"~${cost:.2f}"

    def _show_character_analysis_prompt(self) -> None:
        """Ask if user wants to analyze characters first."""
        self._stage = "analyze_prompt"
        self.print("[#ffffff]?[/] [bold #ffffff]Analyze characters first?[/]")
        self.print("")
        cost = self._estimate_cost_str(0.2)
        cost_hint = f", costs {cost}" if cost else ""
        self.print(f"  [bold #ffffff]Y[/]  Yes [#aaaaaa](identifies characters{cost_hint})[/]")
        self.print("  [bold #ffffff]n[/]  No  [#aaaaaa](skip to transformation)[/]")
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
            self.print("[#ffffff]✓[/] Skipped")
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
            self._pending_characters = characters

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
                        f"[#ffffff]✓[/] Found [bold #ffffff]{char_count}[/] characters [#aaaaaa]({elapsed:.1f}s)[/]"
                    )

                    # Show gender breakdown
                    gender_parts = []
                    for gender, count in by_gender.items():
                        gender_parts.append(f"{count} {gender}")
                    if gender_parts:
                        self.print(f"  [#aaaaaa]Genders:[/] {', '.join(gender_parts)}")

                    # Show top characters
                    if main_chars:
                        self.print("")
                        self.print("  [#aaaaaa]Main characters:[/]")
                        for name in main_chars[:5]:
                            self.print(f"    [#ffffff]•[/] {name}")
                        if len(main_chars) > 5:
                            self.print(f"    [#aaaaaa]... and {len(main_chars) - 5} more[/]")

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

                self.print(f"\n[#ffffff]Analysis failed:[/] {error_msg}")
                self.print("[#aaaaaa]  See logs/tui_debug.log for details[/]")
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

            self.print(f"\n[#ffffff]Error:[/] {error_msg}")
            self.print("[#aaaaaa]  See logs/tui_debug.log for full traceback[/]")
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
                "[#aaaaaa]Add your API keys to[/] [bold #ffffff].env[/] [#aaaaaa]in the project folder:[/]"
            )
            self.print("[#aaaaaa]  OPENAI_API_KEY=sk-...[/]")
            self.print("[#aaaaaa]  DEFAULT_PROVIDER=openai[/]")
            self.print("[#aaaaaa]Then restart the app.[/]")

    def _handle_transform_input(self, value: str) -> None:
        """Handle transform selection."""
        if value.lower() in ("back", "b"):
            self._show_character_analysis_prompt()
            return

        try:
            idx = int(value) - 1
            if 0 <= idx < len(self.TRANSFORM_TYPES):
                self._selected_transform = self.TRANSFORM_TYPES[idx][0]
                self.transform_type = self._selected_transform
                self.print(f"[#ffffff]✓[/] {self._selected_transform}")
                self._show_options_menu()
                return
        except ValueError:
            for name, _ in self.TRANSFORM_TYPES:
                if value.lower() == name.lower():
                    self._selected_transform = name
                    self.transform_type = name
                    self.print(f"[#ffffff]✓[/] {name}")
                    self._show_options_menu()
                    return

        self.print(f"[#ffffff]Enter 1-{len(self.TRANSFORM_TYPES)}[/]")

    def _show_model_menu(self) -> None:
        """Kick off async model detection then render the selection menu."""
        from dotenv import load_dotenv

        load_dotenv()
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        has_openai = bool(openai_key and not openai_key.startswith("your-"))
        has_anthropic = bool(anthropic_key and not anthropic_key.startswith("your-"))

        if not has_openai and not has_anthropic:
            self.print("[#aaaaaa]No API keys configured — skipping model selection[/]")
            self._model_choices = []
            self._show_character_analysis_prompt()
            return

        self.print("[#aaaaaa]Detecting available models...[/]")
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
                        costs = _lookup_model_cost(m.id)
                        pricing = (
                            f"${costs[0]:.2f} / ${costs[1]:.2f} per 1M tokens"
                            if costs
                            else "pricing unknown"
                        )
                        display = _versioned_display_name(
                            m.id, getattr(m, "display_name", m.id)
                        )
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
                    costs = _lookup_model_cost(m.id)
                    pricing = (
                        f"${costs[0]:.2f} / ${costs[1]:.2f} per 1M tokens"
                        if costs
                        else "pricing unknown"
                    )
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
            self.print(f"[#ffffff]✓[/] Using [bold #ffffff]{display_name}[/]")
            self._recalculate_cost(model_id)
            self.print("")
            self._show_character_analysis_prompt()
            return

        self._stage = "model"
        self._model_showing_all = False
        self._render_model_list(show_all=False)

    def _render_model_list(self, show_all: bool = False) -> None:
        """Print the numbered model list."""
        choices = self._model_choices
        current = _get_resolved_model()
        visible = choices if show_all else choices[:5]
        tokens = self._book_stats.get("tokens", 0) if self._book_stats else 0
        self.print("[#ffffff]?[/] [bold #ffffff]Select a model[/]")
        self.print("")
        for i, (model_id, display_name, pricing) in enumerate(visible, 1):
            is_current = model_id == current or current.startswith(model_id)
            marker = " [#aaaaaa]◄ default[/]" if is_current else ""
            rec = " [bold #ffffff]★ recommended[/]" if _is_recommended_model(model_id) else ""
            time_est = _estimate_transform_time(model_id, tokens)
            time_tag = f"  [#666666]{time_est}[/]" if time_est else ""
            self.print(
                f"  [bold #ffffff]{i}[/]  {display_name:<26} [#aaaaaa]{pricing}[/]{time_tag}{rec}{marker}"
            )
        if not show_all and len(choices) > 5:
            self.print(
                f"  [bold #ffffff]M[/]  [#aaaaaa]More models ({len(choices) - 5} additional)...[/]"
            )
        self.print("")
        self.set_prompt(">  ")

    def _handle_model_input(self, value: str) -> None:
        """Handle model selection."""
        choices = self._model_choices
        if not choices:
            self._show_character_analysis_prompt()
            return

        if value.lower() == "m":
            self._model_showing_all = True
            self._render_model_list(show_all=True)
            return

        visible = choices if self._model_showing_all else choices[:5]
        try:
            idx = int(value) - 1
            if 0 <= idx < len(visible):
                model_id, display_name, _ = visible[idx]
                os.environ["DEFAULT_MODEL"] = model_id
                self.print(f"[#ffffff]✓[/] {display_name}")
                self._recalculate_cost(model_id)
                self.print("")
                self._show_character_analysis_prompt()
                return
        except ValueError:
            pass

        for model_id, display_name, _ in choices:
            if value.lower() in (model_id.lower(), display_name.lower()):
                os.environ["DEFAULT_MODEL"] = model_id
                self.print(f"[#ffffff]✓[/] {display_name}")
                self._recalculate_cost(model_id)
                self.print("")
                self._show_character_analysis_prompt()
                return

        limit = len(choices) if self._model_showing_all else min(5, len(choices))
        self.print(f"[#ffffff]Enter 1-{limit}[/]")

    def _recalculate_cost(self, model: str) -> None:
        """Recalculate cost estimate for the selected model and update header."""
        if not self._book_stats:
            return
        tokens = self._book_stats.get("tokens", 0)
        costs = _lookup_model_cost(model)
        estimated_cost = (
            (tokens / 1_000_000 * costs[0]) + (tokens / 1_000_000 * costs[1]) if costs else None
        )
        self._book_stats["estimated_cost"] = estimated_cost
        display = next(
            (name for mid, name, _ in self._model_choices if mid == model),
            _friendly_model_name(model),
        )
        self._book_stats["model"] = display
        with contextlib.suppress(Exception):
            self.query_one(HeaderBar).update_meta(self._book_stats)

    @work(exclusive=True)
    async def _run_name_review(self) -> None:
        """Fetch AI name suggestions and show review menu."""
        if not self._pending_characters:
            # No character analysis was run — skip straight to processing
            self._start_processing()
            return

        # Show loader while fetching suggestions
        loader_start = time.time()
        loader = BrailleLoader("Suggesting names", loader_start)
        with contextlib.suppress(Exception):
            self.query_one("#content", ContentArea).add_widget(loader)

        suggestions: list[dict] = []
        try:
            from dotenv import load_dotenv

            from src.app import Application

            load_dotenv()
            app = Application("src/config.json")
            character_service = app.get_service("character")
            suggestions = await character_service.suggest_name_alternatives(
                self._pending_characters,
                self._selected_transform or "",
            )
            app.shutdown()
        except Exception:
            suggestions = []
        finally:
            with contextlib.suppress(Exception):
                loader.stop()
                loader.remove()

        self._name_suggestions = suggestions
        self._show_name_review_menu()

    def _show_name_review_menu(self) -> None:
        """Show numbered list of suggested name changes."""
        self._stage = "name_review"
        self._name_edit_mode = False
        self._name_custom_mode = False

        if not self._name_suggestions:
            self.print("[#555555]No name suggestions — you can add custom mappings or skip[/]")
            self.print("")
            self.print("  [#aaaaaa]M[/] add mapping  [#aaaaaa]K[/] skip")
            self.print("")
            self.set_prompt(">  ")
            return

        n = len(self._name_suggestions)
        self.print("[#aaaaaa]Suggested name changes:[/]")
        self.print("")
        for i, suggestion in enumerate(self._name_suggestions, 1):
            orig = suggestion["original"]
            sugg = suggestion["suggested"]
            self.print(
                f"  [bold #ffffff]{i}[/]  [#ffffff]{orig:<18}[/] [#aaaaaa]→[/]  [#ffffff]{sugg}[/]"
            )
        self.print("")
        self.print(
            f"  [#aaaaaa]A[/] accept all  [#aaaaaa]K[/] keep originals"
            f"  [#aaaaaa]1-{n}[/] edit entry  [#aaaaaa]M[/] add custom"
        )
        self.print("")
        self.set_prompt(">  ")

    def _handle_name_review_input(self, value: str) -> None:
        """Handle A/K/M/number input on the name review menu."""
        if self._name_custom_mode:
            # User is entering a custom "Original=Target" mapping
            raw = value.strip()
            if raw and "=" in raw:
                parts = raw.split("=", 1)
                orig, target = parts[0].strip(), parts[1].strip()
                if orig and target:
                    self._name_suggestions.append({"original": orig, "suggested": target})
                    self.print(f"[#ffffff]✓[/] Added: {orig} → {target}")
                    self.print("")
                    self._show_name_review_menu()
                    return
            self.print("[#555555]Skipped (use Original=Target format, e.g. Lizzy=Eddie)[/]")
            self.print("")
            self._name_custom_mode = False
            self._show_name_review_menu()
            return

        if self._name_edit_mode:
            # User typed a replacement name for the current entry
            idx = self._name_review_idx
            if value.strip():
                self._name_suggestions[idx]["suggested"] = value.strip()
                sugg = self._name_suggestions[idx]
                self.print(f"[#ffffff]✓[/] Updated: {sugg['original']} → {sugg['suggested']}")
            else:
                self.print("[#555555]No change[/]")
            self._name_edit_mode = False
            self.print("")
            self._show_name_review_menu()
            return

        v = value.strip().lower()
        if v in ("a", ""):  # Accept all (A or Enter)
            self._name_map = {s["original"]: s["suggested"] for s in self._name_suggestions}
            n = len(self._name_map)
            label = "character" if n == 1 else "characters"
            self.print(f"[#ffffff]✓[/] {n} {label} renamed")
            self.print("")
            self._start_processing()
        elif v == "k":  # Keep originals
            self._name_map = None
            self.print("[#555555]Keeping original names[/]")
            self._start_processing()
        elif v == "m":  # Add custom mapping
            self._name_custom_mode = True
            self.print("[#aaaaaa]Enter mapping as Original=Target (e.g. Lizzy=Eddie):[/]")
            self.set_prompt(">  ")
        else:
            # Try to parse as a number for inline editing
            try:
                n = int(value.strip())
                if 1 <= n <= len(self._name_suggestions):
                    idx = n - 1
                    self._name_review_idx = idx
                    self._name_edit_mode = True
                    orig = self._name_suggestions[idx]["original"]
                    curr = self._name_suggestions[idx]["suggested"]
                    self.print(
                        f"[#aaaaaa]New name for [#ffffff]{orig}[/]"
                        f" [#aaaaaa](currently [#ffffff]{curr}[/]):[/]"
                    )
                    self.set_prompt(f"  {orig} → ")
                else:
                    self.print(
                        f"[#ffffff]Enter A, K, M, or a number 1-{len(self._name_suggestions)}[/]"
                    )
            except ValueError:
                self.print(
                    f"[#ffffff]Enter A, K, M, or a number 1-{len(self._name_suggestions)}[/]"
                )

    def _handle_options_input(self, value: str) -> None:
        """Handle options."""
        if value.lower() in ("n", "no"):
            self._no_qc = True
            self.print("[#ffffff]✓[/] QC disabled")
        else:
            self._no_qc = False
            self.print("[#ffffff]✓[/] QC enabled")

        self.print("")
        self._start_processing()

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
            input_bar.disable()
        except Exception:
            pass

        self.print(f"{gradient_text('Starting transformation', ['#ffffff', '#aaaaaa'])}...")

        # Show braille loader with elapsed timer
        self._transform_loader = BrailleLoader("Transforming", self._process_start)
        with contextlib.suppress(Exception):
            self.query_one("#content", ContentArea).add_widget(self._transform_loader)

        # Build result for callback
        self._result = {
            "input": str(self._selected_book),
            "transform_type": self._selected_transform,
            "no_qc": self._no_qc,
            "output_path": str(self._output_path) if self._output_path else None,
            "name_map": self._name_map,
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

            debug_log.info("Calling process_book (await)...")

            def on_chapter_complete(done: int, total: int, _title: str) -> None:
                if self._transform_loader:
                    self._transform_loader._activity = f"Transforming · Ch {done}/{total}"

            result = await app.process_book(
                file_path=self._result["input"],
                transform_type=self._result["transform_type"],
                output_path=self._result.get("output_path"),
                name_map=self._result.get("name_map"),
                custom_title=self._custom_title or None,
                on_chapter_complete=on_chapter_complete,
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
                    eta_str = f" [#aaaaaa]~{int(remaining)}s left[/]"
                else:
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    eta_str = f" [#aaaaaa]~{mins}m {secs}s left[/]"

        # Build gradient progress bar (green)
        bar_width = 50
        filled = int(bar_width * pct)
        empty = bar_width - filled

        # Gradient colors for filled portion
        gradient_colors = [
            "#ffffff",
            "#dddddd",
            "#bbbbbb",
            "#999999",
            "#777777",
            "#555555",
        ]
        filled_chars = []
        for i in range(filled):
            progress_in_fill = i / max(1, filled - 1) if filled > 1 else 0
            color_idx = int(progress_in_fill * (len(gradient_colors) - 1))
            color = gradient_colors[color_idx]
            filled_chars.append(f"[{color}]━[/]")

        filled_str = "".join(filled_chars)
        empty_str = f"[#ffffff]{'━' * empty}[/]"
        bar = filled_str + empty_str

        # Percentage color
        pct_color = "#ffffff"

        # Stage name with green gradient
        stage_gradient = gradient_text(stage_name, ["#ffffff", "#aaaaaa"])

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
            stage_gradient = gradient_text(stage_name, ["#ffffff", "#aaaaaa"])
            msg = f"[#ffffff]✓[/] {stage_gradient} [#aaaaaa]({event.elapsed_seconds:.1f}s)[/]"
            if stats:
                msg += f" [#aaaaaa]— {stats}[/]"
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
            self.print("[#ffffff]⚠ Transformation completed but output file not found[/]")
            self.print(f"  [#aaaaaa]Expected:[/] {output_path}")
            self.print(f"  [#aaaaaa]Time:[/] {elapsed:.1f}s (suspicious if < 5s)")
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

        self.print("")
        self.print(f"[#ffffff]✓[/] {gradient_text('Transformation complete!', ['#ffffff', '#aaaaaa'])}")
        self.print(f"  [#aaaaaa]Time:[/] [#ffffff]{elapsed:.1f}s[/]")
        self.print(f"  [#aaaaaa]Saved:[/] [#ffffff]{self._json_output_path}[/]")

        # Show export options from FORMATS
        self._stage = "export"
        self._export_format_list = list(FORMATS.keys())
        self.print("")
        self.print("[#ffffff]?[/] [bold #ffffff]Export format[/]")
        self.print("")
        for i, key in enumerate(self._export_format_list, 1):
            info = FORMATS[key]
            self.print(f"  [bold #ffffff]{i}[/]  {key:<15} [#aaaaaa]{info['description']}[/]")
        skip_num = len(self._export_format_list) + 1
        self.print(f"  [bold #ffffff]{skip_num}[/]  skip [#aaaaaa](JSON only)[/]")
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
            self.print("[#ffffff]✓[/] Skipped export")
            self._show_final()
            return

        format_map = {str(i): k for i, k in enumerate(format_list, 1)}
        format_map.update({k: k for k in format_list})
        format_map["text"] = "txt"
        format_key = format_map.get(value.lower() if value else "")
        if not format_key:
            self.print(f"[#ffffff]Enter 1-{skip_num} or format key[/]")
            return

        if not self._json_output_path:
            self.print(
                "[#ffffff]⚠[/] [#aaaaaa]No JSON output path available. Transformation may have saved to a different location.[/]"
            )
            self._show_final()
            return

        # Do the export
        try:
            from pathlib import Path

            json_path = Path(self._json_output_path)
            output_path = export_book(str(json_path), format_key)
            self.print(f"[#ffffff]✓[/] Exported to [#ffffff]{output_path}[/]")
        except Exception as e:
            self.print(f"[#ffffff]Export error:[/] {e}")

        self._show_final()

    def _show_final(self) -> None:
        """Offer to transform another book or quit."""
        self._stage = "done"
        self.print("")
        self.print("[#ffffff]?[/] [bold #ffffff]What next?[/]")
        self.print("")
        if self._selected_book:
            book_name = self._selected_book.stem
            self.print(f"  [bold #ffffff]1[/]  Transform [#aaaaaa]{book_name}[/] again [#aaaaaa](different type)[/]")
        else:
            self.print("  [bold #ffffff]1[/]  Transform same book again")
        self.print("  [bold #ffffff]2[/]  Transform a different book")
        self.print("  [bold #ffffff]3[/]  Quit")
        self.print("")
        self.status_text = "Complete ✓"

        try:
            input_bar = self.query_one(InputBar)
            input_bar.stop_loading_animation(restore="[#ffffff]✓[/]  ")
            input_bar.enable()
        except Exception:
            pass

    def _handle_done_input(self, value: str) -> None:
        """Handle post-completion menu: restart or quit."""
        if value in ("1", "again", "a", "y", "yes"):
            self._restart_same_book()
        elif value in ("2", "b", "book"):
            self._restart_flow()
        elif value in ("3", "q", "quit", "exit", ""):
            self.exit()
        else:
            self.print("[#ffffff]Enter 1, 2, or 3[/]")

    def _restart_same_book(self) -> None:
        """Reset transform state only, keeping the selected book, and jump to transform menu."""
        saved_book = self._selected_book
        saved_stats = self._book_stats
        self._restart_flow()
        # Restore book so user skips file selection
        self._selected_book = saved_book
        self._book_stats = saved_stats
        if saved_book:
            self.book_title = saved_book.stem
        # Jump straight to model selection
        self.print("")
        self._show_model_menu()

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
        self.print("[#ffffff]─[/]" * 50)
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
        self.print(f"[bold #ffffff]✗ Error:[/bold #ffffff] {error}")
        self.print("")
        self.status_text = "Error"

        self._stage = "done"
        self.print("[#ffffff]?[/] [bold #ffffff]What next?[/]")
        self.print("")
        self.print("  [bold #ffffff]1[/]  Try another book")
        self.print("  [bold #ffffff]2[/]  Quit")
        self.print("")
        try:
            input_bar = self.query_one(InputBar)
            input_bar.stop_loading_animation(restore="[#ffffff]✗[/]  ")
            input_bar.enable()
        except Exception:
            pass

    def create_progress_context(self) -> ProgressContext:
        """Create progress context for external use."""
        return ProgressContext(
            on_progress=self._on_progress,
            on_stage_complete=self._on_stage_complete,
        )

    def get_result(self) -> dict | None:
        """Get the selection result."""
        return self._result


# =============================================================================
# Entry Points
# =============================================================================


def run_tui(process_callback: Callable | None = None) -> dict | None:
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


def run_selection() -> dict | None:
    """Run selection only (no processing), return result for external processing."""
    app = RegenderTUI(process_callback=None)
    app.run()
    return app.get_result()
