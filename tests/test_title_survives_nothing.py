"""A title the transform replaces may not survive the rename.

An all_female run offered these, and Jason stopped it when he saw them:

    'Mr. Bennet'   -> 'Mr. Thomas Bennet'
    'Mr. Hurst'    -> 'Mr. Gilbert Hurst'
    'Mr. Philips'  -> 'Mr. Edmund Philips'
    'Mr. Gardiner' -> 'Mr. Edward Gardiner'
    'Mr. Collins'  -> 'Mr. William Collins'

Five characters left as men, wearing a man's forename, in a book whose whole
point is that there are no men in it.

check_rename says nothing about them. A character the book names only by title
and family name has no given name of their own, so every given-name check sits
behind `if orig_given:` and is skipped -- and the title was nobody's job at all.
That is the fourth defect of the day with one anatomy: a check skipped for a
good reason, where the skip is wider than the reason.

The rule is narrow on purpose. It fires only when the gendered title comes
through untouched. A *different* title is the model's business -- "Sir William
Lucas" -> "Dame Wilhelmina Lucas" is a correct answer, and so is "Ms." for
"Mrs." -- and refusing those would cost the book correct renames.
"""

import json
from pathlib import Path

import pytest

from src.models.character import CharacterAnalysis
from src.services.name_engine import check_title, screen_renames

FIXTURE = Path(__file__).parent / "fixtures" / "pride-and-prejudice-cast.json"


@pytest.fixture(scope="module")
def cast():
    return CharacterAnalysis.from_dict(json.loads(FIXTURE.read_text()))


THE_FIVE = [
    ("Mr. Bennet", "Mr. Thomas Bennet"),
    ("Mr. Hurst", "Mr. Gilbert Hurst"),
    ("Mr. Philips", "Mr. Edmund Philips"),
    ("Mr. Gardiner", "Mr. Edward Gardiner"),
    ("Mr. Collins", "Mr. William Collins"),
]


class TestTheRunThatWasStopped:
    @pytest.mark.parametrize(("original", "suggested"), THE_FIVE)
    def test_each_one_is_refused(self, cast, original, suggested):
        accepted, reasons = screen_renames([(original, suggested)], cast, transform="all_female")
        assert accepted == [], reasons

    @pytest.mark.parametrize(("original", "suggested"), THE_FIVE)
    def test_the_reason_names_the_title(self, cast, original, suggested):
        _accepted, reasons = screen_renames([(original, suggested)], cast, transform="all_female")
        assert any("keeps the title" in r for r in reasons), reasons

    def test_the_same_character_renamed_properly_is_kept(self, cast):
        """Refusing is only right if the correct answer still gets through."""
        accepted, reasons = screen_renames(
            [("Mr. Bennet", "Mrs. Beatrice Bennet")], cast, transform="all_female"
        )
        assert len(accepted) == 1, reasons


class TestWhatItMustNotCost:
    @pytest.mark.parametrize(
        ("transform", "original", "suggested"),
        [
            # A different title is a correct answer, whichever one it is.
            ("all_female", "Sir William Lucas", "Dame Wilhelmina Lucas"),
            ("all_female", "Mr. Bennet", "Ms. Beatrice Bennet"),
            # Descriptions and possessives lead with a word, not a title.
            ("all_female", "The late Mr. Darcy", "The late Mrs. Darcy"),
            ("all_female", "Wickham's father", "Wickham's mother"),
            ("all_female", "The Archbishop", "The Abbess"),
            # A bare given name has no title to keep.
            ("all_female", "Richard", "Rosalind"),
            ("all_female", "John", "Joan"),
        ],
    )
    def test_correct_renames_survive(self, cast, transform, original, suggested):
        accepted, reasons = screen_renames([(original, suggested)], cast, transform=transform)
        assert len(accepted) == 1, reasons

    def test_a_title_this_transform_leaves_alone_is_not_policed(self):
        """ "Mrs." is untouched by all_female, so keeping it is no defect."""
        assert check_title("Mrs. Bennet", "Mrs. Beatrice Bennet", "all_female") is None

    def test_a_rank_is_not_a_gendered_title(self):
        assert check_title("Colonel Fitzwilliam", "Colonel Frederica", "all_female") is None

    def test_an_unknown_transform_gets_no_opinion(self):
        assert check_title("Mr. Bennet", "Mr. Thomas Bennet", "not_a_transform") is None


class TestTheOtherTransforms:
    def test_all_male_refuses_a_kept_mrs(self, cast):
        accepted, reasons = screen_renames(
            [("Mrs. Bennet", "Mrs. Beatrice Bennet")], cast, transform="all_male"
        )
        assert accepted == [], reasons

    def test_nonbinary_refuses_a_kept_mr(self, cast):
        accepted, reasons = screen_renames(
            [("Mr. Bennet", "Mr. Thomas Bennet")], cast, transform="nonbinary"
        )
        assert accepted == [], reasons
