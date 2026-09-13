"""A live decision announces itself by moving.

Every other line in the interface is still, so a sweep of light across a heading
says "this one is waiting for you" without spending a word on it -- and stopping
the moment it is answered makes a still heading mean "already dealt with".

The one trap here cost an hour and names nothing useful when it fires. Widget
has its own _render, so a method of that name on a subclass hands Textual a
string where it expects a renderable, and the compositor reports "'str' object
has no attribute 'render_strips'" from a frame that mentions neither the class
nor the collision.
"""

import asyncio

import pytest
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll

from src.cli.tui import ShimmerLine, shimmer_markup


class TestTheSweep:
    def test_the_lit_character_follows_the_phase(self):
        text = "abcdefghijklmnop"
        early = shimmer_markup(text, 1)
        late = shimmer_markup(text, 12)
        assert early != late

        def brightest(markup):
            import re

            pairs = re.findall(r"\[#([0-9a-f]{6})\]([^\[])\[/\]", markup)
            return max(pairs, key=lambda p: int(p[0][:2], 16))[1]

        assert brightest(early) in "abc"
        assert brightest(late) in "lmn"

    def test_spaces_are_left_alone(self):
        """A coloured space is invisible and only makes the markup longer."""
        assert "[#" not in shimmer_markup("   ", 1)

    def test_a_heading_carrying_markup_is_returned_untouched(self):
        """Colouring it character by character would break the tags."""
        original = "[bold]already marked up[/]"
        assert shimmer_markup(original, 3) == original

    def test_every_character_survives(self):
        import re

        text = "? Same person? 2 of 9"
        plain = re.sub(r"\[/?[^\]]*\]", "", shimmer_markup(text, 5))
        assert plain == text


class TestTheWidget:
    def test_it_does_not_override_textuals_own_render(self):
        """The whole reason this class has _frame_markup and not _render."""
        from textual.widget import Widget

        assert "_render" not in vars(ShimmerLine)
        assert hasattr(Widget, "_render"), (
            "if Textual drops _render this guard is obsolete, not wrong"
        )

    @pytest.mark.parametrize(
        "args",
        [("? Same person? 1 of 9",), ("? Editorial call 1 of 11", "ch10 p0"), ("?",)],
    )
    def test_it_mounts_in_a_real_app(self, args):
        """Built with its first frame, because Textual may draw a widget before
        on_mount has run and a bare "" is not something it can draw."""

        class Probe(App):
            def compose(self) -> ComposeResult:
                yield VerticalScroll(id="box")

        async def run():
            app = Probe()
            async with app.run_test() as pilot:
                await app.query_one("#box").mount(ShimmerLine(*args))
                await pilot.pause()
                await pilot.pause()

        asyncio.run(run())

    def in_app(self, make, check):
        """Textual widgets need a running loop even to be constructed."""

        class Probe(App):
            def compose(self) -> ComposeResult:
                yield VerticalScroll(id="box")

        async def run():
            app = Probe()
            async with app.run_test() as pilot:
                widget = make()
                await app.query_one("#box").mount(widget)
                await pilot.pause()
                check(widget)

        asyncio.run(run())

    def test_it_settles_when_answered(self):
        def check(line):
            assert line._running is True, "it sweeps while the question stands"
            line.stop()
            assert line._running is False, "and stops once it is answered"

        self.in_app(lambda: ShimmerLine("? Same person? 1 of 9"), check)

    def test_the_suffix_never_sweeps(self):
        """Where a finding is, is context rather than the question."""

        def check(line):
            assert "[#666666]ch10 p0[/]" in line._frame_markup()

        self.in_app(lambda: ShimmerLine("? Editorial call 1 of 11", "ch10 p0"), check)
