"""Two characters still landing on one name once the map is applied.

A character the book names only by title and family name carries no map entry:
an all_female run turns "Mr. Bennet" into "Mrs. Bennet" through the term map,
which is the term map's job and not the name map's. So when "Mr. Bennet" and
"Mrs. Bennet" both land on "Mrs. Bennet", there is nothing in the map for
audit_name_map to read, and it reports a clean map for a book in which five
married couples have become five people.

That is what refusing a suggestion leaves behind when nothing replaces it, and
it happened: the title rule correctly refused "Mr. Bennet" -> "Mr. Thomas
Bennet", and with no replacement the Bennets, Collinses, Gardiners, Hursts and
Philipses each collapsed into one person, invisibly, with the audit calling the
map clean.

Both fixtures are real maps a real run produced. The first version of these
tests used hand-made maps of four or five entries, so pairs the real map
resolves came back as collisions and the rule looked broken when it was not --
the same mistake as fixing an unrealistic fixture instead of the rule.
"""

import json
from pathlib import Path

import pytest

from src.models.character import CharacterAnalysis
from src.models.transformation import TransformType
from src.services.character_service import CharacterService

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def cast():
    return CharacterAnalysis.from_dict(
        json.loads((FIXTURES / "pride-and-prejudice-cast.json").read_text())
    )


@pytest.fixture(scope="module")
def whole_map():
    """The all_female map as a run produced it, every couple told apart."""
    return json.loads((FIXTURES / "all-female-map.json").read_text())


@pytest.fixture(scope="module")
def missing_five():
    """The same map with the five refused entries gone: the regression."""
    return json.loads((FIXTURES / "all-female-map-missing-five.json").read_text())


def check(cast, kind, name_map):
    return CharacterService.unresolved_collisions(cast, TransformType(kind), name_map)


COUPLES = ["Bennet", "Collins", "Gardiner", "Hurst", "Philips"]


class TestTheRegression:
    def test_it_catches_exactly_the_five(self, cast, missing_five):
        found = check(cast, "all_female", missing_five)
        assert len(found) == 5, found

    @pytest.mark.parametrize("surname", COUPLES)
    def test_each_couple_by_name(self, cast, missing_five, surname):
        found = check(cast, "all_female", missing_five)
        assert any(surname in line for line in found), found

    def test_the_whole_map_is_quiet(self, cast, whole_map):
        assert check(cast, "all_female", whole_map) == []

    def test_one_side_renamed_is_enough(self, cast, missing_five):
        """They only have to be told apart, not both moved."""
        half = dict(missing_five)
        half["Mr. Bennet"] = "Mrs. Harriet Bennet"
        assert not any("Bennet" in line for line in check(cast, "all_female", half))


class TestItDoesNotCryWolf:
    def test_a_character_the_transform_does_not_touch_is_not_a_collision(self, cast, missing_five):
        """In an all_female run Jane is already female and goes nowhere, so
        pairing her with her mother is a character colliding with somebody
        standing still."""
        found = check(cast, "all_female", missing_five)
        assert not any("Miss Bennet" in line for line in found), found

    def test_a_rename_by_given_name_tells_them_apart(self, cast, missing_five):
        """Charles Bingley becomes Clara Bingley in this map, so "Mr. Bingley"
        cannot be confused with "Mrs. Bingley" afterwards."""
        found = check(cast, "all_female", missing_five)
        assert not any("Bingley" in line for line in found), found

    def test_each_pair_is_said_once(self, cast, missing_five):
        found = check(cast, "all_female", missing_five)
        assert len(found) == len(set(found))

    def test_an_empty_map_is_not_a_verdict_about_the_book(self, cast):
        """With nothing decided yet everything collides, which is true and
        useless. It must not crash, and it must not be silent either."""
        assert len(check(cast, "all_female", {})) > 5
