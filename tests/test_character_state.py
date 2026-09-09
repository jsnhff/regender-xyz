"""Character state that changes partway through a book.

A cast is not static. Darcy is unmarried for sixty chapters and married in the
sixty-first; Collins marries in twenty-two, Wickham in forty-nine. Anything
that reads a character's state once and applies it to the whole book is wrong
for most of it -- and a gender swap has to know, because English women's
titles encode marital status and men's do not.
"""

import pytest

from src.models.character import Character, Gender
from src.services.character_state import (
    detect_marital_changes,
    initial_marital_state,
    marital_title_maps,
    state_at,
)
from src.services.transform_service import TransformService


def person(name, gender, title):
    return Character(name=name, gender=gender, pronouns={}, aliases=[name], titles=[title])


def book(chapters):
    """chapters: {number: text} or {number: [para, para, ...]}"""
    out = []
    for n, body in sorted(chapters.items()):
        paras = [body] if isinstance(body, str) else list(body)
        out.append({"number": n, "paragraphs": [{"sentences": [t]} for t in paras]})
    return {"chapters": out}


@pytest.fixture
def cast():
    return [
        person("Mr. Darcy", Gender.MALE, "Mr."),
        person("Mr. Bennet", Gender.MALE, "Mr."),
        person("Mrs. Bennet", Gender.FEMALE, "Mrs."),
    ]


class TestDetectingTheChange:
    def test_a_wedding_partway_through_is_found(self, cast):
        changes = detect_marital_changes(
            book({1: "Mr. Darcy was proud.", 2: "Mr. Darcy rode out.", 3: "Mrs. Darcy was glad."}),
            cast,
        )
        marriage = [c for c in changes if c.character == "Mr. Darcy"]
        assert len(marriage) == 1
        assert marriage[0].chapter == 3
        assert marriage[0].becomes == "married"

    def test_a_couple_present_from_the_start_is_not_a_wedding(self, cast):
        """Mrs. Bennet is his wife, not him having married in chapter two."""
        changes = detect_marital_changes(
            book({1: "Mr. Bennet was dry.", 2: "Mrs. Bennet was querulous."}), cast
        )
        assert [c for c in changes if c.character == "Mr. Bennet"] == []

    def test_married_from_the_first_mention_reports_nothing(self, cast):
        changes = detect_marital_changes(book({1: "Mrs. Bennet spoke first."}), cast)
        assert changes == []

    def test_the_evidence_is_recorded(self, cast):
        changes = detect_marital_changes(
            book({1: "Mr. Darcy was proud.", 2: "They visited Mrs. Darcy that spring."}), cast
        )
        assert "Mrs. Darcy" in changes[0].evidence


class TestInitialState:
    def test_a_man_with_a_wife_in_the_cast_opens_married(self, cast):
        """Mr. Bennet never marries during the book; he starts that way."""
        assert initial_marital_state(cast)["Mr. Bennet"] == "married"

    def test_a_man_with_no_counterpart_opens_unmarried(self, cast):
        assert initial_marital_state(cast)["Mr. Darcy"] == "unmarried"

    def test_changes_alone_would_get_bennet_wrong(self, cast):
        """The reason initial state exists: no change fires for him at all."""
        changes = detect_marital_changes(book({1: "Mr. Bennet and Mrs. Bennet."}), cast)
        assert state_at(changes, "Mr. Bennet", "marital", 61) is None
        initial = initial_marital_state(cast)
        assert state_at(changes, "Mr. Bennet", "marital", 61, initial=initial) == "married"


class TestResolvingAcrossChapters:
    def test_the_state_flips_at_the_right_chapter(self, cast):
        changes = detect_marital_changes(
            book({1: "Mr. Darcy was proud.", 5: "Mrs. Darcy was glad."}), cast
        )
        initial = initial_marital_state(cast)
        assert state_at(changes, "Mr. Darcy", "marital", 4, initial=initial) == "unmarried"
        assert state_at(changes, "Mr. Darcy", "marital", 5, initial=initial) == "married"
        assert state_at(changes, "Mr. Darcy", "marital", 61, initial=initial) == "married"


class TestTitleMaps:
    def test_an_unmarried_man_opens_as_miss_and_becomes_mrs(self, cast):
        changes = detect_marital_changes(
            book({1: "Mr. Darcy was proud.", 5: "Mrs. Darcy was glad."}), cast
        )
        base, timeline = marital_title_maps(cast, changes, initial_marital_state(cast))
        assert base["Mr. Darcy"] == "Miss Darcy"
        assert timeline == [(5, 0, {"Mr. Darcy": "Mrs. Darcy"})]

    def test_a_man_married_throughout_never_changes(self, cast):
        changes = detect_marital_changes(book({1: "Mr. Bennet and Mrs. Bennet."}), cast)
        base, timeline = marital_title_maps(cast, changes, initial_marital_state(cast))
        assert base["Mr. Bennet"] == "Mrs. Bennet"
        assert all("Mr. Bennet" not in entries for _, _, entries in timeline)

    def test_women_are_left_alone(self, cast):
        """Miss and Mrs. already say what Mr. does not; only Mr. is ambiguous."""
        base, _ = marital_title_maps(cast, [], initial_marital_state(cast))
        assert "Mrs. Bennet" not in base


class TestTheTransformUsesIt:
    def test_the_map_differs_on_either_side_of_the_wedding(self):
        service = TransformService.__new__(TransformService)
        service.set_title_timeline([(5, 0, {"Mr. Darcy": "Mrs. Darcy"})])
        base = {"Mr. Darcy": "Miss Darcy"}
        assert service._name_map_at(4, 0, base)["Mr. Darcy"] == "Miss Darcy"
        assert service._name_map_at(5, 0, base)["Mr. Darcy"] == "Mrs. Darcy"
        assert service._name_map_at(61, 0, base)["Mr. Darcy"] == "Mrs. Darcy"

    def test_a_service_with_no_timeline_is_unaffected(self):
        """Every existing caller sets none and must behave exactly as before."""
        service = TransformService.__new__(TransformService)
        base = {"Mr. Darcy": "Ms. Darcy"}
        assert service._name_map_at(61, 0, base) is base

    def test_the_base_map_is_not_mutated(self):
        service = TransformService.__new__(TransformService)
        service.set_title_timeline([(5, 0, {"Mr. Darcy": "Mrs. Darcy"})])
        base = {"Mr. Darcy": "Miss Darcy"}
        service._name_map_at(61, 0, base)
        assert base["Mr. Darcy"] == "Miss Darcy"


class TestMidChapterChange:
    """A wedding does not wait for a chapter break."""

    def test_the_paragraph_is_recorded_not_just_the_chapter(self, cast):
        changes = detect_marital_changes(
            book(
                {
                    1: ["Mr. Darcy was proud.", "Mr. Darcy rode out."],
                    2: [
                        "Mr. Darcy called that morning.",
                        "The service was short.",
                        "Mrs. Darcy was glad of it.",
                    ],
                }
            ),
            cast,
        )
        change = next(c for c in changes if c.character == "Mr. Darcy")
        assert (change.chapter, change.paragraph) == (2, 2)

    def test_the_title_flips_inside_one_chapter(self, cast):
        changes = detect_marital_changes(
            book(
                {
                    1: ["Mr. Darcy was proud."],
                    2: ["Mr. Darcy called.", "The service was short.", "Mrs. Darcy was glad."],
                }
            ),
            cast,
        )
        base, timeline = marital_title_maps(cast, changes, initial_marital_state(cast))
        service = TransformService.__new__(TransformService)
        service.set_title_timeline(timeline)

        # same chapter, either side of the wedding
        assert service._name_map_at(2, 1, base)["Mr. Darcy"] == "Miss Darcy"
        assert service._name_map_at(2, 2, base)["Mr. Darcy"] == "Mrs. Darcy"

    def test_state_at_respects_the_paragraph(self, cast):
        changes = detect_marital_changes(
            book({1: ["Mr. Darcy was proud."], 2: ["Mr. Darcy called.", "Mrs. Darcy was glad."]}),
            cast,
        )
        initial = initial_marital_state(cast)
        assert state_at(changes, "Mr. Darcy", "marital", 2, 0, initial) == "unmarried"
        assert state_at(changes, "Mr. Darcy", "marital", 2, 1, initial) == "married"
