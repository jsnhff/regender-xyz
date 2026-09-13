"""A granted forename has to suit the gender the transform is producing.

An all-female run offered "Mrs. Edward Gardiner" and "Mrs. Edmund Philips" on
every single attempt. Not carelessness: Edward Gardiner is Mr. Gardiner's first
name in Austen's own text, so the model is recalling the book rather than
ignoring the instruction -- which is why saying "MUST BECOME FEMALE" in the
prompt took it from three wrong in five to two, and no further.

Measured on the real path, three runs per transform, counting only forenames
granted to characters the book never named:

    prompt alone      6 wrong of 14   (all_female)
    with this check   0 wrong of  7   (all_female)
                      0 wrong of 16   (all_male)

The rule refuses; it does not approve. A name positively in the wrong list is
rejected and the character falls through to the engine; a name in neither list
passes, because the lists cannot be complete and refusing what they have not
heard of would cost the book most of its correct renames.
"""

import json
from pathlib import Path

import pytest

from src.models.character import CharacterAnalysis, Gender
from src.services.given_names import FEMALE, MALE, NEUTRAL, reads_as
from src.services.name_engine import check_given_gender, screen_renames

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def cast():
    return CharacterAnalysis.from_dict(
        json.loads((FIXTURES / "pride-and-prejudice-cast.json").read_text())
    )


class TestTheLists:
    def test_no_name_is_in_two_of_them(self):
        """A name in both is a name the rule would answer two ways."""
        assert not (MALE & FEMALE)
        assert not (MALE & NEUTRAL)
        assert not (FEMALE & NEUTRAL)

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Edward", "male"),
            ("Edmund", "male"),
            ("Thomas", "male"),
            ("Henrietta", "female"),
            ("Margaret", "female"),
            # The engine's own neutral pool must read as neutral, or the
            # nonbinary edition loses its best answers.
            ("Francis", "neutral"),
            ("Evelyn", "neutral"),
            ("Sidney", "neutral"),
            ("Hilary", "neutral"),
            ("Vivian", "neutral"),
            ("Meredith", "neutral"),
            ("Clare", "neutral"),
            ("Aubrey", "neutral"),
            # Not in the lists, and that is an answer too.
            ("Almeria", "unknown"),
            ("Zebediah", "unknown"),
        ],
    )
    def test_it_reads_them_the_way_english_does(self, name, expected):
        assert reads_as(name) == expected


class TestTheRule:
    def test_the_two_that_came_back_every_run(self, cast):
        for original, suggested in (
            ("Mr. Gardiner", "Mrs. Edward Gardiner"),
            ("Mr. Philips", "Mrs. Edmund Philips"),
        ):
            accepted, reasons = screen_renames(
                [(original, suggested)], cast, transform="all_female"
            )
            assert accepted == [], reasons
            assert any("female" in r for r in reasons), reasons

    def test_the_right_answer_for_the_same_character_passes(self, cast):
        accepted, reasons = screen_renames(
            [("Mr. Gardiner", "Mrs. Margaret Gardiner")], cast, transform="all_female"
        )
        assert len(accepted) == 1, reasons

    def test_all_male_refuses_a_womans_name(self, cast):
        accepted, reasons = screen_renames(
            [("Mrs. Gardiner", "Mr. Henrietta Gardiner")], cast, transform="all_male"
        )
        assert accepted == [], reasons


class TestWhatItMustNotCost:
    def test_a_name_it_has_never_heard_of_passes(self, cast):
        """The lists cannot be complete, and the engine's pool is far larger."""
        accepted, reasons = screen_renames(
            [("Mr. Gardiner", "Mrs. Almeria Gardiner")], cast, transform="all_female"
        )
        assert len(accepted) == 1, reasons

    @pytest.mark.parametrize("name", ["Francis", "Evelyn", "Hilary", "Vivian"])
    def test_a_neutral_name_suits_any_transform(self, name):
        for wants in (Gender.FEMALE, Gender.MALE):
            assert check_given_gender(f"Mrs. {name} Gardiner", wants) is None

    def test_nonbinary_wants_a_name_used_across_genders(self):
        assert check_given_gender("Mx. Edward Gardiner", Gender.NONBINARY) is not None
        assert check_given_gender("Mx. Francis Gardiner", Gender.NONBINARY) is None

    def test_a_character_the_transform_leaves_alone_is_not_judged(self):
        assert check_given_gender("Mrs. Edward Gardiner", None) is None

    def test_the_title_is_not_read_as_the_name(self):
        """ "Mrs." leads the string; "Edward" is the name being judged."""
        assert check_given_gender("Mrs. Margaret Gardiner", Gender.FEMALE) is None
