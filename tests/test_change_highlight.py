"""Point at the word the question is about.

The review stepper shows the source line and the transformed line and asks for
a ruling. The reader had to find the difference for themselves, in two nearly
identical lines of Regency prose -- and both lines were cut at 66 characters
from their start, so when the changed word sat past that column it was not on
screen at all. The one word the question was about was the one word missing.
"""

import re

import pytest

from src.cli.tui import _mark_changes

CHANGED = "#e5c07b"


def marked(line):
    """The words rendered as changed."""
    return re.findall(r"\[bold " + CHANGED + r"\]([^\[]+)\[/\]", line)


def plain(line):
    """The line as the reader sees it, markup removed."""
    return re.sub(r"\[/?[^\]]*\]", "", line).strip()


class TestTheChangedWordIsMarked:
    def test_one_word_apart(self):
        was, now = _mark_changes(
            "she talked of Mrs. Darcy with great satisfaction",
            "they talked of Mx. Darcy with great satisfaction",
        )
        assert marked(was) == ["she", "Mrs."]
        assert marked(now) == ["they", "Mx."]

    def test_the_unchanged_words_are_not_marked(self):
        was, now = _mark_changes("his uncle was there", "their uncle was there")
        assert "uncle" not in marked(was)
        assert marked(now) == ["their"]

    def test_an_identical_pair_marks_nothing(self):
        was, now = _mark_changes("nothing changed here", "nothing changed here")
        assert marked(was) == []
        assert marked(now) == []


class TestTheChangeIsBroughtIntoView:
    """Windowing on the change, not on the start of the line."""

    def test_a_late_change_is_shown(self):
        prefix = "It is a truth universally acknowledged that a single man in possession of a "
        was, now = _mark_changes(
            prefix + "good fortune must be in want of a wife",
            prefix + "good fortune must be in want of a spouse",
        )
        assert "wife" in marked(was)
        assert "spouse" in marked(now)
        # And the reader can see it, which is the point.
        assert "wife" in plain(was)
        assert "spouse" in plain(now)

    def test_the_window_stays_within_the_width(self):
        long_line = " ".join(f"word{i}" for i in range(80))
        was, _ = _mark_changes(long_line + " wife", long_line + " spouse")
        assert len(plain(was)) <= 72  # 66 plus the ellipsis marker

    def test_an_elision_is_shown_when_text_is_dropped(self):
        long_line = " ".join(f"word{i}" for i in range(80))
        was, _ = _mark_changes(long_line + " wife", long_line + " spouse")
        assert "…" in plain(was)

    def test_a_short_line_is_not_elided(self):
        was, now = _mark_changes("his uncle", "their uncle")
        assert "…" not in plain(was)
        assert "…" not in plain(now)


class TestWholesaleDifference:
    """With nothing in common there is no changed word to point at."""

    def test_nothing_is_marked_when_the_lines_share_little(self):
        was, now = _mark_changes(
            "one two three four five",
            "alpha beta gamma delta epsilon",
        )
        assert marked(was) == []
        assert marked(now) == []

    def test_but_the_text_still_renders(self):
        was, now = _mark_changes("one two three", "alpha beta gamma")
        assert plain(was) == "one two three"
        assert plain(now) == "alpha beta gamma"


class TestEdges:
    @pytest.mark.parametrize(
        "before,after",
        [("", ""), ("", "something"), ("something", "")],
    )
    def test_an_empty_side_does_not_raise(self, before, after):
        was, now = _mark_changes(before, after)
        assert isinstance(was, str)
        assert isinstance(now, str)

    def test_markup_is_balanced(self):
        """An unclosed tag swallows the rest of the screen."""
        was, now = _mark_changes("his uncle was there", "their uncle was there")
        for line in (was, now):
            assert line.count("[/]") == len(re.findall(r"\[(?!/)[^\]]*\]", line))
