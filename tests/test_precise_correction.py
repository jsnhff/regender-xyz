"""A correction lands where it was reported, and can be accepted rather than typed.

Chapter 61 of Pride and Prejudice says "his aunt" of Lady Catherine early on,
and "her uncle and aunt" of the Gardiners much later in the same paragraph.
Both arrive as "his uncle". Correcting the second to "his uncles" rewrote the
first as well, and turned one aunt into two uncles in a finished book.
"""

import json
import re
from pathlib import Path

import pytest

from src.cli.tui import RegenderTUI

SENTENCES = [
    "Resistance on the part of his uncle gave way.",
    "But the visits of his uncle and uncle from the city continued.",
]


def pattern(term):
    return re.compile(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])")


class TestOnlyTheReportedOne:
    def test_the_later_occurrence_is_changed(self):
        """The offset points into the second sentence."""
        offset = len(SENTENCES[0]) + 1 + SENTENCES[1].index("his uncle")
        out = RegenderTUI._replace_once(SENTENCES, pattern("his uncle"), "his uncles", offset)
        assert out[1].startswith("But the visits of his uncles and uncle")

    def test_the_earlier_one_is_untouched(self):
        offset = len(SENTENCES[0]) + 1 + SENTENCES[1].index("his uncle")
        out = RegenderTUI._replace_once(SENTENCES, pattern("his uncle"), "his uncles", offset)
        assert out[0] == SENTENCES[0], "Lady Catherine must stay one person"

    def test_the_earlier_occurrence_can_be_targeted(self):
        offset = SENTENCES[0].index("his uncle")
        out = RegenderTUI._replace_once(SENTENCES, pattern("his uncle"), "his uncles", offset)
        assert out[0].startswith("Resistance on the part of his uncles")
        assert out[1] == SENTENCES[1]

    def test_only_one_sentence_changes(self):
        offset = len(SENTENCES[0]) + 1 + SENTENCES[1].index("his uncle")
        out = RegenderTUI._replace_once(SENTENCES, pattern("his uncle"), "his uncles", offset)
        assert sum(1 for a, b in zip(SENTENCES, out) if a != b) == 1

    def test_the_whole_phrase_replaces_cleanly(self):
        offset = len(SENTENCES[0]) + 1 + SENTENCES[1].index("his uncle and uncle")
        out = RegenderTUI._replace_once(
            SENTENCES, pattern("his uncle and uncle"), "his uncles", offset
        )
        assert "his uncles from the city" in out[1]
        assert out[0] == SENTENCES[0]


class TestWithoutAnOffset:
    def test_it_behaves_as_it_always_did(self):
        """An older finding with no position still works."""
        out = RegenderTUI._replace_once(SENTENCES, pattern("his uncle"), "his uncles", -1)
        assert out[0] != SENTENCES[0] and out[1] != SENTENCES[1]

    def test_an_offset_past_the_end_still_changes_something(self):
        out = RegenderTUI._replace_once(SENTENCES, pattern("his uncle"), "his uncles", 100_000)
        assert sum(1 for a, b in zip(SENTENCES, out) if a != b) == 1

    def test_a_term_that_is_not_there_changes_nothing(self):
        out = RegenderTUI._replace_once(SENTENCES, pattern("her niece"), "his nephew", 5)
        assert out == SENTENCES


BOOK = {
    "title": "T",
    "chapters": [{"number": 1, "title": "", "paragraphs": [{"sentences": list(SENTENCES)}]}],
}

FINDING = {
    "chapter": 1,
    "paragraph": 0,
    "term": "his uncle and uncle",
    "excerpt": "...visits of his uncle and uncle from the city",
    "source_excerpt": "...visits of her uncle and aunt from the city",
    "suggestion": "his uncles",
    "offset": len(SENTENCES[0]) + 1 + SENTENCES[1].index("his uncle and uncle"),
}


class _Bare(RegenderTUI):
    status_text = ""


@pytest.fixture
def tui(tmp_path):
    path = tmp_path / "all_male.json"
    path.write_text(json.dumps(BOOK), encoding="utf-8")
    (tmp_path / "all_male.txt").write_text("old", encoding="utf-8")
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


def plain(lines):
    return [re.sub(r"\[/?[^\]]*\]", "", line) for line in lines]


class TestAcceptingASuggestion:
    def test_the_suggestion_is_shown(self, tui):
        tui._show_review_menu()
        assert any("his uncles" in line for line in plain(tui._lines))

    def test_the_accept_key_is_offered(self, tui):
        tui._show_review_menu()
        assert any(" a accept" in line for line in plain(tui._lines))

    def test_a_applies_it(self, tui):
        tui._handle_review_input("a")
        book = json.loads(Path(tui._json_output_path).read_text(encoding="utf-8"))
        assert "his uncles from the city" in book["chapters"][0]["paragraphs"][0]["sentences"][1]

    def test_a_is_recorded_as_a_decision(self, tui):
        tui._handle_review_input("a")
        assert tui._review_items[0]["decision"] == "his uncles"

    def test_a_leaves_the_other_sentence_alone(self, tui):
        tui._handle_review_input("a")
        book = json.loads(Path(tui._json_output_path).read_text(encoding="utf-8"))
        assert book["chapters"][0]["paragraphs"][0]["sentences"][0] == SENTENCES[0]

    def test_a_without_a_suggestion_is_not_a_replacement(self, tui):
        """Otherwise "a" would silently become the new text."""
        tui._review_items = [{**FINDING, "suggestion": ""}]
        tui._handle_review_input("a")
        book = json.loads(Path(tui._json_output_path).read_text(encoding="utf-8"))
        assert "his uncle and uncle" in book["chapters"][0]["paragraphs"][0]["sentences"][1]

    def test_no_suggestion_means_no_accept_key(self, tui):
        tui._review_items = [{**FINDING, "suggestion": ""}]
        tui._show_review_menu()
        assert not any(" a accept" in line for line in plain(tui._lines))
