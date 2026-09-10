"""Asking the person the question only a person can answer.

A run reported findings and then went straight to the export menu, so the
count was the end of it. What QC cannot settle by rule is exactly what a
reader settles instantly -- "read three pages" is a book's pages.

The first version printed the whole list and asked for a number. Sixteen
findings at three lines each overflow the screen, the list redrew after every
decision, and nothing said which numbers were already done. So it steps
through them instead.
"""

import json
import re
from pathlib import Path

import pytest

from src.cli.tui import RegenderTUI


def plain(lines):
    return [re.sub(r"\[/?[^\]]*\]", "", line) for line in lines]


BOOK = {
    "title": "T",
    "chapters": [
        {
            "number": 1,
            "title": "",
            "paragraphs": [
                {"sentences": ["He read three pages."]},
                {"sentences": ["The pages of the book."]},
            ],
        },
        {"number": 2, "title": "", "paragraphs": [{"sentences": ["More pages here."]}]},
    ],
}

FINDING = {
    "severity": "needs_review",
    "kind": "residual_term",
    "chapter": 1,
    "paragraph": 0,
    "detail": "'pages' left untransformed",
    "excerpt": "...read three pages, he interrupted",
    "source_excerpt": "...read three pages, she interrupted",
    "term": "pages",
}

SECOND = {**FINDING, "chapter": 2, "paragraph": 0, "term": "pages"}


class _Bare(RegenderTUI):
    """status_text is a Textual reactive; a plain attribute stands in for it."""

    status_text = ""


@pytest.fixture
def tui(tmp_path):
    path = tmp_path / "gender_swap.json"
    path.write_text(json.dumps(BOOK), encoding="utf-8")
    (tmp_path / "gender_swap.txt").write_text("old", encoding="utf-8")

    app = _Bare.__new__(_Bare)
    app._json_output_path = str(path)
    app._review_items = [dict(FINDING)]
    app._review_idx = 0
    app._stage = ""
    app._lines = []
    app.print = app._lines.append
    app.set_prompt = lambda _p: None
    app._accept_input = lambda: None
    app._export_shown = False
    app._show_export_menu = lambda: setattr(app, "_export_shown", True)
    return app


def book_of(tui):
    return json.loads(Path(tui._json_output_path).read_text(encoding="utf-8"))


class TestOneAtATime:
    def test_it_shows_where_it_is(self, tui):
        tui._review_items = [dict(FINDING), dict(SECOND)]
        tui._show_review_menu()
        assert any("1 of 2" in line for line in plain(tui._lines))

    def test_it_shows_only_the_current_one(self, tui):
        tui._review_items = [dict(FINDING), dict(SECOND)]
        tui._show_review_menu()
        assert not any("2 of 2" in line for line in plain(tui._lines))

    def test_it_names_the_word_and_the_place(self, tui):
        tui._show_review_menu()
        text = " ".join(plain(tui._lines))
        assert "pages" in text and "ch1 p0" in text

    def test_it_shows_both_lines(self, tui):
        tui._show_review_menu()
        text = " ".join(plain(tui._lines))
        assert "was" in text and "now" in text

    def test_enter_advances(self, tui):
        tui._review_items = [dict(FINDING), dict(SECOND)]
        tui._handle_review_input("")
        assert tui._review_idx == 1
        assert any("2 of 2" in line for line in plain(tui._lines))

    def test_the_last_one_finishes(self, tui):
        tui._handle_review_input("")
        assert tui._export_shown


class TestDeciding:
    def test_a_replacement_reaches_the_saved_book(self, tui):
        tui._handle_review_input("leaves")
        assert book_of(tui)["chapters"][0]["paragraphs"][0]["sentences"] == [
            "He read three leaves."
        ]

    def test_only_the_flagged_paragraph_changes(self, tui):
        tui._handle_review_input("leaves")
        book = book_of(tui)
        assert book["chapters"][0]["paragraphs"][1]["sentences"] == ["The pages of the book."]
        assert book["chapters"][1]["paragraphs"][0]["sentences"] == ["More pages here."]

    def test_the_text_export_keeps_up(self, tui):
        tui._handle_review_input("leaves")
        text = Path(tui._json_output_path.replace(".json", ".txt")).read_text(encoding="utf-8")
        assert "three leaves" in text

    def test_enter_leaves_it_alone(self, tui):
        tui._handle_review_input("")
        assert book_of(tui)["chapters"][0]["paragraphs"][0]["sentences"] == ["He read three pages."]

    def test_the_word_is_matched_whole(self, tui):
        book = json.loads(json.dumps(BOOK))
        book["chapters"][0]["paragraphs"][0]["sentences"] = ["He read three pages of rampages."]
        Path(tui._json_output_path).write_text(json.dumps(book), encoding="utf-8")
        tui._handle_review_input("leaves")
        assert "rampages" in book_of(tui)["chapters"][0]["paragraphs"][0]["sentences"][0]


class TestGoingBack:
    def test_b_steps_back(self, tui):
        tui._review_items = [dict(FINDING), dict(SECOND)]
        tui._handle_review_input("")
        tui._handle_review_input("b")
        assert tui._review_idx == 0

    def test_back_from_the_first_stays_put(self, tui):
        tui._handle_review_input("b")
        assert tui._review_idx == 0
        assert not tui._export_shown

    def test_a_decision_is_shown_when_you_come_back(self, tui):
        tui._review_items = [dict(FINDING), dict(SECOND)]
        tui._handle_review_input("leaves")
        tui._lines.clear()
        tui._handle_review_input("b")
        assert any("already changed to leaves" in line for line in plain(tui._lines))

    def test_enter_does_not_undo_a_decision(self, tui):
        """Going back and pressing Enter must not silently discard the change."""
        tui._review_items = [dict(FINDING), dict(SECOND)]
        tui._handle_review_input("leaves")
        tui._handle_review_input("b")
        tui._handle_review_input("")
        assert tui._review_items[0]["decision"] == "leaves"


class TestSkippingTheRest:
    def test_s_finishes(self, tui):
        tui._review_items = [dict(FINDING), dict(SECOND)]
        tui._handle_review_input("s")
        assert tui._export_shown

    def test_it_says_how_many_were_kept(self, tui):
        tui._review_items = [dict(FINDING), dict(SECOND)]
        tui._handle_review_input("s")
        assert any("remaining 2" in line for line in plain(tui._lines))

    def test_earlier_decisions_survive(self, tui):
        tui._review_items = [dict(FINDING), dict(SECOND)]
        tui._handle_review_input("leaves")
        tui._handle_review_input("s")
        assert tui._review_items[0]["decision"] == "leaves"
        assert any("1 changed" in line for line in plain(tui._lines))


class TestTheSheet:
    def test_what_was_decided_is_written_down(self, tui, tmp_path):
        tui._handle_review_input("leaves")
        sheet = json.loads((tmp_path / "review_decisions.json").read_text())
        assert sheet["decided"][0]["decision"] == "leaves"

    def test_what_was_kept_is_written_down(self, tui, tmp_path):
        tui._handle_review_input("")
        sheet = json.loads((tmp_path / "review_decisions.json").read_text())
        assert sheet["kept"][0]["term"] == "pages"


class TestItFits:
    def test_every_line_fits_eighty_columns(self, tui):
        tui._show_review_menu()
        for line in plain(tui._lines):
            assert len(line) <= 78, f"too wide: {line!r}"

    def test_a_finding_without_a_source_line_still_renders(self, tui):
        tui._review_items = [{**FINDING, "source_excerpt": ""}]
        tui._show_review_menu()
        assert any("pages" in line for line in plain(tui._lines))

    def test_a_broken_output_path_does_not_crash(self, tui):
        tui._json_output_path = "/nonexistent/dir/x.json"
        tui._handle_review_input("leaves")
        assert any("Could not apply" in line for line in plain(tui._lines))
