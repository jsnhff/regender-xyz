"""Every question is asked the same way.

Fifteen prompt sites had grown fifteen dialects. Headings ended in a second
question mark under the marker that already was one -- "? Analyze characters?"
-- or carried no marker at all. Keys came in four cases: Y/n here, y there, S,
A/K/M/R. The Enter key was written as the glyph, as "Enter", and as "press
Enter". The default was marked by a capital letter, by a row keyed with the
glyph, by a trailing tag, or not at all. And on the last menu of the run bare
Enter quit the program, where bare Enter everywhere else meant "keep what you
have".

These tests pin the grammar rather than the wording, so the prompts can still
be rewritten -- they just cannot go back to being written each in their own way.
"""

import re

import pytest

from src.cli.tui import (
    _ASK,
    _ENTER,
    _VERBS,
    RegenderTUI,
    choice_lines,
    footer_line,
    question_line,
    reject_line,
)

PLAIN = re.compile(r"\[/?[^\]]*\]")


def plain(line):
    return PLAIN.sub("", line)


class TestTheHeading:
    def test_the_marker_is_the_question_mark(self):
        """The complaint that started this: "? Analyze characters?"."""
        text, _ = question_line("Analyze characters?")
        assert text == "Analyze characters"

    def test_a_heading_without_one_is_left_alone(self):
        assert question_line("Select a model")[0] == "Select a model"

    def test_the_location_comes_back_separately(self):
        """It has to, so the heading can sweep while the location does not."""
        text, where = question_line("Same person?", "2 of 9")
        assert (text, where) == ("Same person", "2 of 9")


class TestTheAnswers:
    def test_they_are_numbered_from_one(self):
        lines = [plain(line) for line in choice_lines(["Yes", "No"])]
        assert lines[0].split()[1] == "1"
        assert lines[1].split()[0] == "2"

    def test_exactly_one_answer_wears_the_glyph(self):
        lines = choice_lines(["Yes", "No", "Maybe"], default=2)
        assert sum(_ENTER in line for line in lines) == 1

    def test_the_glyph_sits_on_the_named_default(self):
        """Not always the first row -- the model list defaults to the model
        already configured, wherever it happens to fall."""
        lines = choice_lines(["a", "b", "c"], default=3)
        assert _ENTER in lines[2]

    def test_hints_line_up_into_a_column(self):
        lines = [plain(line) for line in choice_lines([("Short", "x"), ("Much longer", "y")])]
        assert lines[0].index("x") == lines[1].index("y")

    def test_a_label_wearing_markup_is_measured_without_it(self):
        """Measuring the tags instead collapses the column."""
        lines = [
            plain(line) for line in choice_lines([("[bold]Short[/]", "x"), ("Much longer", "y")])
        ]
        assert lines[0].index("x") == lines[1].index("y")

    def test_a_second_line_can_hang_under_an_answer(self):
        """Where the setup menu keeps the address you go to for a key.

        Asserted whole rather than as a substring: a bare `"host" in line`
        reads to a security scanner as a URL check done the unsafe way, and
        the exact row is the stronger claim in any case.
        """
        lines = choice_lines([("Anthropic", "literary", "console.anthropic.com")])
        assert len(lines) == 2
        assert plain(lines[1]).strip() == "console.anthropic.com"


class TestTheVerbs:
    def test_a_verb_keeps_its_letter_everywhere(self):
        """Learning "s" on the cast review should teach it on the editorial one."""
        assert _VERBS["back"][0] == "b"
        assert _VERBS["rest"][0] == "s"

    def test_no_two_verbs_share_a_letter_in_one_question(self):
        for question in (("back", "rest"), ("accept", "keep", "mapping", "again")):
            keys = [_VERBS[verb][0] for verb in question]
            assert len(keys) == len(set(keys)), question

    def test_the_glyph_can_sit_on_a_verb(self):
        """For the one question whose numbers are its data, not its answers."""
        assert _ENTER in footer_line("accept", "keep", default="a")

    def test_and_only_on_the_one_named(self):
        line = footer_line("accept", "keep", default="a")
        assert line.count(_ENTER) == 1
        assert line.index(_ENTER) < line.index("keep")


class TestRefusal:
    def test_it_is_said_one_way(self):
        assert plain(reject_line(3)) == "Enter 1-3"

    def test_the_verbs_are_named_too(self):
        assert plain(reject_line(2, "back", "rest")) == "Enter 1-2, b, s"

    def test_a_single_answer_is_not_written_as_a_range(self):
        assert plain(reject_line(1)) == "Enter 1"


class Fake(RegenderTUI):
    """Plain attributes where the real app has Textual reactives."""

    status_text = ""
    book_title = ""
    transform_type = ""


def render(prepare):
    """One question's worth of screen, without starting the app."""
    app = Fake.__new__(Fake)
    app._lines = []
    app.print = app._lines.append
    app.set_prompt = lambda _p: None
    app._accept_input = lambda: None
    app._live_heading = lambda text, suffix="": app._lines.append(
        f"[bold]{text}[/]   [#666666]{suffix}[/]" if suffix else f"[bold]{text}[/]"
    )
    app._stage = ""
    prepare(app)
    return app._lines


def a_book(app):
    app._show_book_menu()


def a_transform(app):
    app.TRANSFORM_TYPES = RegenderTUI.TRANSFORM_TYPES
    app._show_transform_menu()


def a_title(app):
    app.book_title = "Pride And Prejudice"
    app._custom_title = ""
    app._selected_transform = "all_female"
    app._show_retitle_prompt()


def an_analysis(app):
    app._estimate_cost_str = lambda _f: "2¢"
    app._show_character_analysis_prompt()


def a_pair(app):
    app._cast_candidates = [{"a": "Mary Bennet", "b": "Mary King", "reason": "both called Mary"}]
    app._cast_idx = 0
    app._book_line_for = lambda _n: ""
    app._finish_cast_review = lambda: None
    app._show_cast_candidate()


def a_finding(app):
    app._review_items = [
        {
            "chapter": 10,
            "paragraph": 0,
            "term": "gentleman",
            "suggestion": "person",
            "source_excerpt": "a gentleman of large fortune",
            "excerpt": "a person of large fortune",
        }
    ]
    app._review_idx = 0
    app._finish_review = lambda: None
    app._show_review_menu()


def an_export(app):
    app._show_export_menu()


def a_provider(app):
    app._show_setup_wizard()


QUESTIONS = {
    "book": a_book,
    "transform": a_transform,
    "title": a_title,
    "analysis": an_analysis,
    "cast pair": a_pair,
    "finding": a_finding,
    "export": an_export,
    "provider": a_provider,
}


class TestEveryQuestionOnScreen:
    @pytest.mark.parametrize("name", sorted(QUESTIONS))
    def test_no_heading_asks_twice(self, name):
        for line in render(QUESTIONS[name]):
            assert not plain(line).strip().endswith("?"), line

    @pytest.mark.parametrize("name", sorted(QUESTIONS))
    def test_exactly_one_answer_is_what_enter_gives_you(self, name):
        lines = render(QUESTIONS[name])
        assert sum(_ENTER in line for line in lines) == 1, lines

    @pytest.mark.parametrize("name", sorted(QUESTIONS))
    def test_the_answers_are_numbered_from_one(self, name):
        numbers = []
        for line in render(QUESTIONS[name]):
            match = re.match(r"^.?\s\s?(\d+)\s\s", plain(line))
            if match:
                numbers.append(int(match.group(1)))
        assert numbers == list(range(1, len(numbers) + 1)), numbers


class TestTheMarkerIsNotHandRolled:
    def test_no_site_writes_its_own(self):
        """A hand-written marker is how the dialects started. There is one."""
        import pathlib

        source = pathlib.Path("src/cli/tui.py").read_text()
        written = source.count('"[#ffffff]?[/]')
        assert written == 1, f"{written} hand-written markers; _ASK is the only one"
        assert _ASK == "[#ffffff]?[/]"


class TestEnterIsNeverTheDestructiveAnswer:
    """The property worth having tests for, rather than the look of it."""

    def test_a_merge_is_never_what_a_tired_reader_gets_by_default(self):
        """Two characters merged into one cannot be told apart again by any
        later pass, so it takes saying so."""
        lines = [plain(line) for line in render(a_pair)]
        default = next(line for line in lines if _ENTER in line)
        assert "Two different people" in default

    def test_a_finding_is_kept_by_default_not_rewritten(self):
        lines = [plain(line) for line in render(a_finding)]
        default = next(line for line in lines if _ENTER in line)
        assert "Keep it" in default

    def test_an_export_does_not_write_a_file_by_default(self):
        lines = [plain(line) for line in render(an_export)]
        default = next(line for line in lines if _ENTER in line)
        assert "Skip" in default

    def test_the_run_does_not_end_by_default(self):
        """Bare Enter used to quit here, and meant "keep what you have"
        everywhere else in the same run."""
        app = Fake.__new__(Fake)
        app._lines = []
        app.print = app._lines.append
        app.exited = False
        app.exit = lambda *a: setattr(app, "exited", True)
        app.restarted = False
        app._restart_same_book = lambda: setattr(app, "restarted", True)
        app._handle_done_input("")
        assert not app.exited
        assert app.restarted

    def test_quitting_still_takes_saying_so(self):
        app = Fake.__new__(Fake)
        app._lines = []
        app.print = app._lines.append
        app.exited = False
        app.exit = lambda *a: setattr(app, "exited", True)
        app._handle_done_input("3")
        assert app.exited


class TestTheOldKeysStillWork:
    """Muscle memory outlives a redesign; the letters keep answering."""

    def test_y_still_merges_a_pair(self):
        app = Fake.__new__(Fake)
        app._lines = []
        app.print = app._lines.append
        app._cast_candidates = [{"a": "Mary Bennet", "b": "Mary King", "reason": "r"}]
        app._cast_idx = 0
        app._cast_merges = []
        app._show_cast_candidate = lambda: None
        app._handle_cast_review_input("y")
        assert app._cast_merges

    def test_enter_still_keeps_a_pair_apart(self):
        app = Fake.__new__(Fake)
        app._lines = []
        app.print = app._lines.append
        app._cast_candidates = [{"a": "Mary Bennet", "b": "Mary King", "reason": "r"}]
        app._cast_idx = 0
        app._cast_merges = []
        app._show_cast_candidate = lambda: None
        app._handle_cast_review_input("")
        assert not app._cast_merges

    def test_an_unknown_answer_is_refused_rather_than_taken_as_one(self):
        app = Fake.__new__(Fake)
        app._lines = []
        app.print = app._lines.append
        app._cast_candidates = [{"a": "Mary Bennet", "b": "Mary King", "reason": "r"}]
        app._cast_idx = 0
        app._cast_merges = []
        app._show_cast_candidate = lambda: None
        app._handle_cast_review_input("maybe")
        assert not app._cast_merges
        assert app._cast_idx == 0, "it should still be asking"
        assert any("Enter 1-2" in plain(line) for line in app._lines)


class TestTheMarkupSurvivesTheParser:
    """The app builds every line with Text.from_markup, so a tag that does not
    close leaks into what the reader sees rather than raising anywhere."""

    def parsed(self, line):
        from rich.text import Text

        return Text.from_markup(line).plain

    def test_a_colour_nested_inside_a_hint_closes(self):
        """The model menu puts a dim time inside the hint's own colour."""
        line = choice_lines([("Claude Opus 5", "~$5.70  [#666666]~88 min[/]")])[0]
        assert "[" not in self.parsed(line)

    def test_bold_nested_inside_a_label_closes(self):
        line = choice_lines([("Anthropic [bold #ffffff](Claude)[/]", "literary")])[0]
        assert "(Claude)" in self.parsed(line)
        assert "[" not in self.parsed(line)

    @pytest.mark.parametrize("name", sorted(QUESTIONS))
    def test_every_question_parses(self, name):
        for line in render(QUESTIONS[name]):
            assert "[" not in self.parsed(line), line
