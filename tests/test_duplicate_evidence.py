"""Ask the question with the evidence attached.

"Same person? Mary Bennet / Mary King" is unanswerable by anyone who has not
read the book, and a guess merges two people permanently. The analysis already
knew the answer and never showed it:

    Mary Bennet   Middle Bennet daughter, plain and pedantic, reads great books
    Mary King     Young woman who went to Liverpool, was connected to Wickham

Two entries both reading "Fourth Bennet daughter" are as plainly one person as
those two are plainly not. A line of the book goes alongside where the book
names them outright -- many cast entries are reconstructions it never spells
out, "Mary Bennet" appearing nowhere in Pride and Prejudice though Mary and the
Bennets both do, so the quotation is evidence when it exists and silence when it
does not.
"""

import re

import pytest

from src.cli.tui import RegenderTUI
from src.models.character import Character, CharacterAnalysis, Gender
from src.services.character_service import CharacterService


def person(name, description="", gender=Gender.FEMALE, aliases=()):
    return Character(
        name=name,
        gender=gender,
        pronouns={},
        description=description,
        aliases=list(aliases),
    )


class TestTheCandidateCarriesItsEvidence:
    def test_each_side_brings_its_description(self):
        cast = [
            person("Mary Bennet", "Middle Bennet daughter, plain and pedantic"),
            person("Mary King", "Young woman who went to Liverpool"),
            # A married name is only plausible where somebody could have been
            # married; the rule asks for that and this cast has to supply it.
            person("Thomas Bennet", "Father of the Bennet daughters", Gender.MALE),
        ]
        found = CharacterService.possible_duplicates(cast)
        assert found, "the pair should be offered"
        item = found[0]
        assert "Middle Bennet daughter" in item["a_description"]
        assert "Liverpool" in item["b_description"]

    def test_a_missing_description_is_empty_rather_than_absent(self):
        cast = [
            person("Mary Bennet"),
            person("Mary King"),
            person("Thomas Bennet", "", Gender.MALE),
        ]
        item = CharacterService.possible_duplicates(cast)[0]
        assert item["a_description"] == ""
        assert item["b_description"] == ""


class TestTheCard:
    @pytest.fixture
    def app(self, tmp_path):
        class Bare(RegenderTUI):
            book_title = "—"
            transform_type = "—"
            status_text = ""

        book = tmp_path / "book.txt"
        book.write_text(
            "CHAPTER I\n\nThere is no danger of Wickham's marrying Mary King, "
            "she is gone down to her uncle at Liverpool.\n"
        )

        app = Bare.__new__(Bare)
        app._lines = []
        app.print = app._lines.append
        app.set_prompt = lambda _p: None
        app._accept_input = lambda: None
        app._stage = ""
        app._source_text = None
        app._selected_book = book
        app._output_path = None
        app._json_output_path = None
        app._run_name_review = lambda: None
        app._pending_characters = CharacterAnalysis(
            book_id="t",
            characters=[
                person("Mary Bennet", "Middle Bennet daughter, plain and pedantic"),
                person("Mary King", "Young woman who went to Liverpool"),
                person("Thomas Bennet", "Father of the Bennet daughters", Gender.MALE),
            ],
        )
        return app

    def rendered(self, app):
        return "\n".join(re.sub(r"\[/?[^\]]*\]", "", line) for line in app._lines)

    def test_the_descriptions_are_shown(self, app):
        app._start_cast_review()
        text = self.rendered(app)
        assert "Middle Bennet daughter" in text
        assert "Liverpool" in text

    def test_a_line_of_the_book_is_shown_where_it_names_them(self, app):
        app._start_cast_review()
        text = self.rendered(app)
        assert "Wickham" in text, "the book names Mary King, so quote it"

    def test_a_name_the_book_never_uses_is_not_invented(self, app):
        """ "Mary Bennet" appears nowhere in the book; silence is the honest
        answer, not a line about some other Mary."""
        assert app._book_line_for("Mary Bennet") == ""

    def test_no_book_on_disk_is_not_an_error(self, app):
        app._selected_book = None
        app._source_text = None
        assert app._book_line_for("Mary King") == ""

    def test_the_book_is_read_once(self, app):
        app._book_line_for("Mary King")
        first = app._source_text
        app._book_line_for("Mary Bennet")
        assert app._source_text is first


class TestAgainstTheRealCast:
    """The five cards the reader actually met, each answerable on sight."""

    def test_every_candidate_has_something_to_judge_by(self):
        import json
        import pathlib

        path = pathlib.Path(
            "/Users/jasonhuff/regender-xyz/books/output/pride-and-prejudice/"
            "all_male_2026-09-10_21-44/characters.json"
        )
        if not path.exists():
            pytest.skip("the real cast is not on this machine")

        cast = CharacterAnalysis.from_dict(json.loads(path.read_text()))
        merged, _ = CharacterService._merge_same_person(list(cast.characters))
        candidates = CharacterService.possible_duplicates(merged)

        assert candidates
        bare = [
            f"{c['a']} / {c['b']}"
            for c in candidates
            if not c["a_description"] and not c["b_description"]
        ]
        assert not bare, f"these would be asked with nothing to answer from: {bare}"
