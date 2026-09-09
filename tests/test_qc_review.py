"""Asking the person the question only a person can answer.

A run reported "24 to review" and then went straight to the export menu, so
the count was the end of it. What QC cannot settle by rule is exactly what a
reader settles instantly -- "read three pages" is a book's pages -- and those
last few decisions are the difference between a good transform and a finished
one.
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
        {
            "number": 2,
            "title": "",
            "paragraphs": [{"sentences": ["More pages here."]}],
        },
    ],
}

FINDING = {
    "severity": "needs_review",
    "kind": "residual_term",
    "chapter": 1,
    "paragraph": 0,
    "detail": "'pages' left untransformed",
    "excerpt": "...read three pages, he interrupted",
    "term": "pages",
}


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
    app._review_edit_idx = None
    app._stage = ""
    app._lines = []
    app.print = app._lines.append
    app.set_prompt = lambda _p: None
    app._export_shown = False
    app._show_export_menu = lambda: setattr(app, "_export_shown", True)
    return app


def book_of(tui):
    return json.loads(Path(tui._json_output_path).read_text(encoding="utf-8"))


class TestItAsks:
    def test_the_menu_names_the_word(self, tui):
        tui._show_review_menu()
        assert any("pages" in line for line in plain(tui._lines))

    def test_it_shows_where_and_what_it_looks_like(self, tui):
        tui._show_review_menu()
        text = " ".join(plain(tui._lines))
        assert "ch1 p0" in text
        assert "read three pages" in text

    def test_it_says_how_many_calls_there_are(self, tui):
        tui._show_review_menu()
        assert any("1 editorial call" in line for line in plain(tui._lines))

    def test_two_findings_read_as_plural(self, tui):
        tui._review_items = [dict(FINDING), dict(FINDING)]
        tui._show_review_menu()
        assert any("2 editorial calls" in line for line in plain(tui._lines))


class TestAcceptingADecision:
    def test_a_replacement_reaches_the_saved_book(self, tui):
        tui._show_review_menu()
        tui._handle_review_input("1")
        tui._handle_review_input("leaves")
        assert book_of(tui)["chapters"][0]["paragraphs"][0]["sentences"] == [
            "He read three leaves."
        ]

    def test_only_the_flagged_paragraph_changes(self, tui):
        """'pages' is wrong in one sentence and right in the next."""
        tui._handle_review_input("1")
        tui._handle_review_input("leaves")
        book = book_of(tui)
        assert book["chapters"][0]["paragraphs"][1]["sentences"] == ["The pages of the book."]
        assert book["chapters"][1]["paragraphs"][0]["sentences"] == ["More pages here."]

    def test_the_text_export_is_kept_in_step(self, tui):
        tui._handle_review_input("1")
        tui._handle_review_input("leaves")
        text = Path(tui._json_output_path.replace(".json", ".txt")).read_text(encoding="utf-8")
        assert "three leaves" in text

    def test_an_empty_reply_leaves_it_alone(self, tui):
        tui._handle_review_input("1")
        tui._handle_review_input("")
        assert book_of(tui)["chapters"][0]["paragraphs"][0]["sentences"] == ["He read three pages."]

    def test_the_word_is_matched_whole(self, tui):
        """'pages' must not rewrite the inside of another word."""
        book = json.loads(json.dumps(BOOK))
        book["chapters"][0]["paragraphs"][0]["sentences"] = ["He read three pages of rampages."]
        Path(tui._json_output_path).write_text(json.dumps(book), encoding="utf-8")
        tui._handle_review_input("1")
        tui._handle_review_input("leaves")
        assert "rampages" in book_of(tui)["chapters"][0]["paragraphs"][0]["sentences"][0]


class TestFinishing:
    def test_keeping_everything_moves_on_to_export(self, tui):
        tui._handle_review_input("k")
        assert tui._export_shown

    def test_enter_moves_on_to_export(self, tui):
        tui._handle_review_input("")
        assert tui._export_shown

    def test_what_was_decided_is_written_down(self, tui, tmp_path):
        tui._handle_review_input("1")
        tui._handle_review_input("leaves")
        tui._handle_review_input("")
        sheet = json.loads((tmp_path / "review_decisions.json").read_text())
        assert sheet["decided"][0]["decision"] == "leaves"
        assert sheet["kept"] == []

    def test_keeping_records_that_too(self, tui, tmp_path):
        tui._handle_review_input("k")
        sheet = json.loads((tmp_path / "review_decisions.json").read_text())
        assert sheet["decided"] == []
        assert sheet["kept"][0]["term"] == "pages"

    def test_it_says_what_it_did(self, tui):
        tui._handle_review_input("1")
        tui._handle_review_input("leaves")
        tui._handle_review_input("")
        assert any("1 changed, 0 left" in line for line in plain(tui._lines))


class TestBadInput:
    def test_a_number_out_of_range_is_refused(self, tui):
        tui._handle_review_input("9")
        assert any("Enter a number" in line for line in plain(tui._lines))
        assert not tui._export_shown

    def test_nonsense_does_not_lose_the_run(self, tui):
        tui._handle_review_input("wat")
        assert not tui._export_shown

    def test_a_broken_output_path_does_not_crash(self, tui):
        tui._json_output_path = "/nonexistent/dir/x.json"
        tui._handle_review_input("1")
        tui._handle_review_input("leaves")
        assert any("Could not apply" in line for line in plain(tui._lines))
