"""A way to tell two mothers apart, where the two are not side by side.

The coordinated case already had an answer -- "her uncle and aunt" becoming
"his uncle and uncle" reads better as "his uncles". The separated case had none,
so the reader was shown a problem with nothing to press:

    was  "My mother would have no objection, but my father hates London."
    now  "My mother would have no objection, but my mother hates London."

Ten of these in the all-female Pride and Prejudice. English has an ordinary
answer for it, and it is the one that keeps a daughter sounding like a daughter:

    "My mother would have no objection, but my other mother hates London."

A name -- "but Mrs. Bennet hates London" -- is the other good answer and is
deliberately not suggested. Which mother is meant needs coreference this cannot
do, and a guessed name offered as an answer is worse than no answer; typing one
is already a choice on that screen.

The fixture is the ten real paragraph pairs the run produced, source and output,
so these tests are about sentences Austen wrote.
"""

import json
from pathlib import Path

import pytest

from src.models.transformation import TransformType
from src.services.qc_service import QCService

FIXTURES = Path(__file__).parent / "fixtures"
PAIRS = json.loads((FIXTURES / "collapsed-contrast-paragraphs.json").read_text())
NAME_MAP = json.loads((FIXTURES / "all-female-map.json").read_text())


def findings_for(pair):
    """Every collapsed-contrast finding for one real paragraph."""
    service = QCService(TransformType.ALL_FEMALE, name_map=NAME_MAP)
    source = {"number": pair["chapter"], "paragraphs": [{"sentences": [pair["source"]]}]}
    output = {"number": pair["chapter"], "paragraphs": [{"sentences": [pair["output"]]}]}
    report = service.check_chapter(pair["chapter"] - 1, source, output)
    return [f for f in report.findings if f.kind == "collapsed_contrast"]


def accept(pair, finding):
    """What the paragraph reads once the suggestion is taken."""
    text = pair["output"]
    head, tail = text[: finding.offset], text[finding.offset :]
    return head + tail.replace(finding.term, finding.suggestion, 1)


class TestEveryOneOfThemIsAnswerable:
    @pytest.mark.parametrize(
        "pair", PAIRS, ids=[f"ch{p['chapter']}p{p['paragraph']}" for p in PAIRS]
    )
    def test_the_reader_is_given_something_to_press(self, pair):
        found = findings_for(pair)
        assert found, "the run reported one here"
        assert all(f.suggestion for f in found), [f.detail for f in found]

    @pytest.mark.parametrize(
        "pair", PAIRS, ids=[f"ch{p['chapter']}p{p['paragraph']}" for p in PAIRS]
    )
    def test_the_suggestion_distinguishes_the_two(self, pair):
        for finding in findings_for(pair):
            assert " other " in f" {finding.suggestion} " or finding.suggestion.endswith("s")


class TestItLandsOnTheRightMention:
    """The sentence introduces one parent and then distinguishes the other, so
    the second is the one to mark. Marking the first inverts the sentence."""

    def test_the_one_jason_read_out(self):
        pair = next(p for p in PAIRS if (p["chapter"], p["paragraph"]) == (29, 24))
        finding = findings_for(pair)[0]
        assert accept(pair, finding) == (
            '"My mother would have no objection, but my other mother hates London."'
        )

    def test_a_possessive_survives_it(self):
        pair = next(p for p in PAIRS if (p["chapter"], p["paragraph"]) == (29, 14))
        finding = findings_for(pair)[0]
        assert "her other mother's maiden name" in accept(pair, finding)
        assert "what carriage her mother kept" in accept(pair, finding)

    @pytest.mark.parametrize(
        "pair", PAIRS, ids=[f"ch{p['chapter']}p{p['paragraph']}" for p in PAIRS]
    )
    def test_accepting_changes_exactly_one_mention(self, pair):
        for finding in findings_for(pair):
            before, after = pair["output"], accept(pair, finding)
            assert after != before
            assert after.count(finding.suggestion) == before.count(finding.suggestion) + 1


class TestTheSiblingCaseToo:
    def test_brother_and_sister_get_the_same_treatment(self):
        pair = next(p for p in PAIRS if (p["chapter"], p["paragraph"]) == (45, 7))
        finding = findings_for(pair)[0]
        assert finding.suggestion == "her other sister"


class TestWhatItDoesNotChange:
    def test_the_coordinated_case_still_prefers_a_plural(self):
        """ "her uncle and aunt" -> "his uncle and uncle" is better as one
        plural, and that answer must not be replaced by "his other uncle"."""
        service = QCService(TransformType.ALL_MALE)
        source = {"number": 1, "paragraphs": [{"sentences": ["She saw her uncle and aunt there."]}]}
        output = {"number": 1, "paragraphs": [{"sentences": ["He saw his uncle and uncle there."]}]}
        report = service.check_chapter(0, source, output)
        found = [f for f in report.findings if f.kind == "collapsed_contrast"]
        assert found
        assert found[0].suggestion == "his uncles"
