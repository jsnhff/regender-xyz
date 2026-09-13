"""Enter takes the recommended model.

The return glyph sat on whichever model was already configured, which on a
fresh install resolves to nothing and falls back to row one -- so Enter
recommended nothing while a row below it said "recommended". Jason asked for
the two to agree.

Falls back the way it did before when no model on screen is recommended: the
configured one, then the first row. There is still exactly one glyph.
"""

import re

import pytest

from src.cli.tui import _ENTER, RegenderTUI

PLAIN = re.compile(r"\[/?[^\]]*\]")


def plain(line):
    return PLAIN.sub("", line)


class Fake(RegenderTUI):
    """Plain attributes where the real app has Textual reactives."""

    status_text = ""
    book_title = ""
    transform_type = ""


WITH_A_STAR = [
    ("claude-fable-5-1", "Claude Fable 5.1", "$3/M"),
    ("claude-opus-5", "Claude Opus 5", "$15/M"),
    ("claude-sonnet-5", "Claude Sonnet 5", "$3/M"),
]

WITHOUT_ONE = [
    ("claude-fable-5-1", "Claude Fable 5.1", "$3/M"),
    ("claude-opus-5", "Claude Opus 5", "$15/M"),
]


def model_menu(current="", choices=None):
    app = Fake.__new__(Fake)
    app._lines = []
    app.print = app._lines.append
    app.set_prompt = lambda _p: None
    app._model_choices = choices or WITH_A_STAR
    app._book_stats = {"tokens": 190_000}
    app._model_showing_all = False
    app._warn_about_unpriced_models = lambda: None

    import src.cli.tui as tui

    was = tui._get_resolved_model
    tui._get_resolved_model = lambda: current
    try:
        app._render_model_list(show_all=False)
    finally:
        tui._get_resolved_model = was
    return app


def cursored(app):
    return next(plain(line) for line in app._lines if _ENTER in line)


class TestTheGlyphAndTheStarAgree:
    def test_it_sits_on_the_recommended_model(self):
        assert "Claude Sonnet 5" in cursored(model_menu())

    def test_the_row_it_sits_on_is_the_one_carrying_the_star(self):
        line = cursored(model_menu())
        assert "recommended" in line, line

    def test_it_stays_there_when_another_model_is_configured(self):
        """The recommendation is the point of the menu; a stale env var is not."""
        assert "Claude Sonnet 5" in cursored(model_menu(current="claude-opus-5"))

    def test_enter_resolves_to_that_row(self):
        assert model_menu()._model_default == 3


class TestWhatHappensWithoutAStar:
    def test_it_falls_back_to_the_configured_model(self):
        app = model_menu(current="claude-opus-5", choices=WITHOUT_ONE)
        assert "Claude Opus 5" in cursored(app)

    def test_and_to_the_first_row_when_there_is_neither(self):
        assert model_menu(choices=WITHOUT_ONE)._model_default == 1


class TestTheGrammarStillHolds:
    @pytest.mark.parametrize(
        ("current", "choices"),
        [("", WITH_A_STAR), ("claude-opus-5", WITH_A_STAR), ("claude-opus-5", WITHOUT_ONE)],
    )
    def test_exactly_one_row_is_cursored(self, current, choices):
        app = model_menu(current=current, choices=choices)
        assert sum(_ENTER in line for line in app._lines) == 1
