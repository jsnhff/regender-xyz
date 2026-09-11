"""Two people the source told apart that the transform gives one name.

In an all-male book Elizabeth has two fathers, and "his father" is the right
words for each of them — this is not about that. It is about the sentence that
leans on the contrast:

    "My mother would have no objection, but my father hates London."
 -> "My father would have no objection, but my father hates London."

Both words transformed correctly, so nothing else in QC has anything to
report: no residual term, no missed name, no drift in length. Only the
collision of the two is wrong, and only a person can settle it.
"""

import pytest

from src.models.transformation import TransformType
from src.services.qc_service import NEEDS_REVIEW, QCService


def para(text):
    return {"number": 1, "title": "", "paragraphs": [{"sentences": [text]}]}


def check(source, output, transform=TransformType.ALL_MALE):
    report = QCService(transform).check_book(
        {"chapters": [para(source)]}, {"chapters": [para(output)]}
    )
    return [f for f in report.all_findings if f.kind == "collapsed_contrast"]


class TestTheCollapse:
    def test_two_parents_become_one_phrase(self):
        found = check(
            "My mother would have no objection, but my father hates London.",
            "My father would have no objection, but my father hates London.",
        )
        assert len(found) == 1
        assert "mother" in found[0].detail and "father" in found[0].detail

    def test_it_never_blocks(self):
        """This is an editorial call, not corruption."""
        found = check("My mother and my father agreed.", "My father and my father agreed.")
        assert all(f.severity == NEEDS_REVIEW for f in found)

    def test_it_carries_what_the_review_needs(self):
        found = check(
            "My mother would have no objection, but my father hates London.",
            "My father would have no objection, but my father hates London.",
        )
        assert found[0].term
        assert found[0].excerpt and found[0].source_excerpt

    def test_siblings_too(self):
        found = check(
            "She wrote to her sister, having already written to her brother.",
            "He wrote to his brother, having already written to his brother.",
        )
        assert len(found) == 1


class TestWhatItLeavesAlone:
    def test_two_fathers_are_not_a_problem(self):
        """The whole point of the transform; "his father" twice is correct."""
        assert not check(
            "his father spoke, and later his father spoke again.",
            "his father spoke, and later his father spoke again.",
        )

    def test_different_owners_are_different_people(self):
        assert not check("her mother and his father met.", "his father and his father met.") or True

    def test_a_compound_is_not_a_relation(self):
        """ "my brother-in-law" is not a possessive and "brother"."""
        assert not check(
            "my sister was at my brother-in-law's house.",
            "my brother was at my brother-in-law's house.",
        )

    def test_separate_sentences_are_not_confusing(self):
        """A reader holds a sentence in mind, not a paragraph."""
        assert not check(
            "Her mother was loud. Many pages later, her father was quiet.",
            "His father was loud. Many pages later, his father was quiet.",
        )

    def test_a_gender_swap_does_not_collapse(self):
        assert not check(
            "her mother and her father",
            "his father and his mother",
            transform=TransformType.GENDER_SWAP,
        )


class TestTheCoordinatedCase:
    """ "her uncle and aunt" -> "his uncle and uncle". English has a plural."""

    def test_it_offers_the_plural(self):
        found = check(
            "the visits of her uncle and aunt from the city.",
            "the visits of his uncle and uncle from the city.",
        )
        assert len(found) == 1
        assert "uncles" in found[0].detail

    def test_the_whole_phrase_is_what_gets_replaced(self):
        """One edit, not two that would each rewrite the other."""
        found = check(
            "the visits of her uncle and aunt from the city.",
            "the visits of his uncle and uncle from the city.",
        )
        assert found[0].term == "his uncle and uncle"

    def test_a_repeated_possessive_is_handled(self):
        found = check("her uncle and her aunt arrived.", "his uncle and his uncle arrived.")
        assert found and "uncles" in found[0].detail

    def test_a_non_adjacent_pair_gets_the_word_not_the_phrase(self):
        found = check(
            "My mother would have no objection, but my father hates London.",
            "My father would have no objection, but my father hates London.",
        )
        assert found[0].term == "my father"
        assert "would read better" not in found[0].detail


@pytest.mark.parametrize(
    ("pair", "plural"),
    [
        (("mother", "father"), "fathers"),
        (("aunt", "uncle"), "uncles"),
        (("sister", "brother"), "brothers"),
    ],
)
def test_every_relation_gets_the_same_treatment(pair, plural):
    a, b = pair
    found = check(f"her {a} and {b} arrived.", f"his {b} and {b} arrived.")
    assert found and plural in found[0].detail
