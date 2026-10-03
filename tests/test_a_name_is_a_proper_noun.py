# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""A name map may not rewrite a common noun that happens to spell a name.

Pen Harrington is a real character in Pride and Prejudice -- "Harriet was ill,
and so Pen was forced to come by herself" -- so the map holds "Pen". The
substitution alternation is case-insensitive because the *term* map needs it to
be, and `_match_case` then lowers the replacement to match what it found. So
Austen's pen became a person, in three of the four printed editions:

    "I am afraid you do not like your peter. Let me mend it for you.
     I mend pens remarkably well."

    "Adieu! I take up my peter again to do, what I have just told you
     I would not"

QC scored all three editions at 99.8-100% coverage with no findings, because
nothing about the defect is gendered.

Case sensitivity alone is the wrong fix: Gutenberg signs letters in full
capitals, so "LYDIA BENNET." has to keep matching its map entry.
"""

import pytest

from src.services.transform_service import TransformService


@pytest.fixture
def svc():
    return TransformService.__new__(TransformService)


# The real entry, from the all_male and nonbinary runs of 2026-09-13.
PEN_MAP = {"Pen": "Peter", "Harriet": "Harold", "Lydia": "Lionel"}


class TestTheCommonNounSurvives:
    """The two sentences that reached print."""

    @pytest.mark.parametrize(
        "text",
        [
            "I am afraid you do not like your pen. Let me mend it for you.",
            "I mend pens remarkably well.",
            "Adieu! I take up my pen again to do, what I have just told you",
            "she laid down her pen",
        ],
    )
    def test_a_lower_case_pen_is_not_renamed(self, svc, text):
        out = svc._apply_name_map(text, PEN_MAP, source_text=text)
        assert out == text
        assert "peter" not in out.lower()


class TestTheNameStillLands:
    """The guard must not cost the character her rename."""

    def test_the_capitalised_name_is_renamed(self, svc):
        source = "Harriet was ill, and so Pen was forced to come by herself"
        out = svc._apply_name_map(source, PEN_MAP, source_text=source)
        assert out == "Harold was ill, and so Peter was forced to come by herself"

    def test_a_name_in_full_capitals_still_matches(self, svc):
        """Gutenberg signs letters this way: "LYDIA BENNET." """
        source = "Your affectionate friend, LYDIA BENNET."
        out = svc._apply_name_map(source, PEN_MAP, source_text=source)
        assert out == "Your affectionate friend, LIONEL BENNET."

    def test_a_name_opening_a_sentence_still_matches(self, svc):
        source = "Pen was forced to come by herself."
        out = svc._apply_name_map(source, PEN_MAP, source_text=source)
        assert out.startswith("Peter was forced")

    def test_the_possessive_still_matches(self, svc):
        source = "Pen's bonnet was ugly."
        out = svc._apply_name_map(source, PEN_MAP, source_text=source)
        assert out == "Peter's bonnet was ugly."


class TestAMapKeyThatIsAlreadyLowerCase:
    """No key in a real name map is lower case, but the rule should be honest."""

    def test_it_keeps_matching_either_casing(self, svc):
        source = "the pen and the Pen"
        out = svc._apply_name_map(source, {"pen": "quill"}, source_text=source)
        assert out == "the quill and the Quill"


class TestTheWholePenParagraph:
    """Both senses in one breath, which is what made this hard to see."""

    def test_the_name_changes_and_the_noun_does_not(self, svc):
        source = "Pen asked for a pen, and Pen mended the pen."
        out = svc._apply_name_map(source, PEN_MAP, source_text=source)
        assert out == "Peter asked for a pen, and Peter mended the pen."
