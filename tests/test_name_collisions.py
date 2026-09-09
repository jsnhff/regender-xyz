"""A rename must never turn one character into another one.

Reproduces the Sep-2026 all_female sample. The map carried
"Mr. Bennet" -> "Mrs. Bennet" while Mrs. Bennet was already the mother, and
"Mr. Hurst" -> "Mrs. Hurst" while Mrs. Hurst was already Bingley's sister.
Both were applied by a bare dict update that skipped every check the engine
runs on its own proposals.

Downstream the damage did not look like a rename bug at all: the model
invented "Ms." to keep the collided pairs apart and then spread it
inconsistently, so Mrs. Long -- female from the start, and never renamed --
came out as "Ms. Long" eight times out of ten.
"""

import asyncio

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.name_engine import NameEngine


def _person(name, gender, title):
    return Character(name=name, gender=gender, pronouns={}, aliases=[name], titles=[title])


def bennets():
    return CharacterAnalysis(
        book_id="pp",
        characters=[
            _person("Mr. Bennet", Gender.MALE, "Mr."),
            _person("Mrs. Bennet", Gender.FEMALE, "Mrs."),
            _person("Elizabeth Bennet", Gender.FEMALE, "Miss"),
        ],
    )


def build(base_map, cast=None):
    engine = NameEngine(provider=None)
    return asyncio.run(
        engine.build_name_map(cast or bennets(), TransformType.ALL_FEMALE, base_map=base_map)
    )


class TestSuppliedMapCollision:
    def test_the_father_is_not_turned_into_the_mother(self):
        name_map, report = build({"Mr. Bennet": "Mrs. Bennet"})
        assert name_map.get("Mr. Bennet") != "Mrs. Bennet"

    def test_the_refusal_is_reported_not_silent(self):
        """A dropped rename has to be visible, or the book reads fine and is wrong."""
        _, report = build({"Mr. Bennet": "Mrs. Bennet"})
        assert any("already" in flag for flag in report["flags"]), report["flags"]

    def test_a_supplied_rename_with_no_collision_still_wins(self):
        """Supplied entries outrank the engine everywhere except a merge."""
        name_map, _ = build({"Mr. Bennet": "Ms. Beaumont"})
        assert name_map["Mr. Bennet"] == "Ms. Beaumont"

    def test_periods_do_not_hide_a_collision(self):
        """ "Mrs Bennet" and "Mrs. Bennet" are the same person."""
        name_map, _ = build({"Mr. Bennet": "Mrs Bennet"})
        assert name_map.get("Mr. Bennet") != "Mrs Bennet"

    def test_the_hurst_case(self):
        cast = CharacterAnalysis(
            book_id="pp",
            characters=[
                _person("Mr. Hurst", Gender.MALE, "Mr."),
                _person("Mrs. Hurst", Gender.FEMALE, "Mrs."),
            ],
        )
        name_map, _ = build({"Mr. Hurst": "Mrs. Hurst"}, cast=cast)
        assert name_map.get("Mr. Hurst") != "Mrs. Hurst"

    def test_renaming_someone_to_their_own_name_is_not_a_collision(self):
        """A no-op entry must not be reported as merging a character with itself."""
        _, report = build({"Mrs. Bennet": "Mrs. Bennet"})
        assert not any("already" in flag for flag in report["flags"]), report["flags"]


class TestSwapIsNotAMerge:
    """A swap exchanges two names; nobody ends up sharing one.

    The first version of this guard refused both halves of
    "Mr. Bennet" <-> "Mrs. Bennet" and would have silently disabled every
    family rename in a gender_swap run.
    """

    def test_an_exchange_is_allowed(self):
        engine = NameEngine(provider=None)
        name_map, report = asyncio.run(
            engine.build_name_map(
                bennets(),
                TransformType.GENDER_SWAP,
                base_map={"Mr. Bennet": "Mrs. Bennet", "Mrs. Bennet": "Mr. Bennet"},
            )
        )
        assert name_map["Mr. Bennet"] == "Mrs. Bennet"
        assert name_map["Mrs. Bennet"] == "Mr. Bennet"
        assert report["flags"] == []

    def test_a_one_way_move_onto_an_occupied_name_is_still_refused(self):
        """Only one half supplied: the mother is not vacating, so this merges."""
        name_map, _ = build({"Mr. Bennet": "Mrs. Bennet"})
        assert name_map.get("Mr. Bennet") != "Mrs. Bennet"

    def test_a_no_op_entry_does_not_count_as_vacating(self):
        """ "Mrs. Bennet" keeping its name means the move still merges."""
        name_map, _ = build({"Mr. Bennet": "Mrs. Bennet", "Mrs. Bennet": "Mrs. Bennet"})
        assert name_map.get("Mr. Bennet") != "Mrs. Bennet"
