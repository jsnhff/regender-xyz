"""Two characters must not become one person.

A woman known only as "Mrs. Bennet" has no given name of her own, so an
all_male transform can only swap her title -- and lands her on Mr. Bennet, her
husband. Nine of Pride and Prejudice's cast do this going one way and five
going the other. Nothing downstream can separate them afterwards.

A gender swap never hits it: names are exchanged, not merged. That is why five
chapters and a full swap edition ran clean without this ever surfacing.
"""

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.character_service import CharacterService

find = CharacterService._name_collisions


def cast(*specs):
    return CharacterAnalysis(
        book_id="t",
        characters=[Character(name=n, gender=g, pronouns={}) for n, g in specs],
    )


BENNETS = cast(("Mr. Bennet", Gender.MALE), ("Mrs. Bennet", Gender.FEMALE))


def women(analysis):
    return [c for c in analysis.characters if c.gender == Gender.FEMALE]


def men(analysis):
    return [c for c in analysis.characters if c.gender == Gender.MALE]


class TestTheMerge:
    def test_a_married_couple_collides_going_male(self):
        found = find(BENNETS, women(BENNETS), TransformType.ALL_MALE)
        assert found["Mrs. Bennet"]["candidate"] == "Mr. Bennet"
        assert found["Mrs. Bennet"]["clashes_with"] == "Mr. Bennet"

    def test_and_going_female(self):
        found = find(BENNETS, men(BENNETS), TransformType.ALL_FEMALE)
        assert found["Mr. Bennet"]["candidate"] == "Mrs. Bennet"

    def test_a_swap_never_collides(self):
        """Names are exchanged, not merged — which is why this stayed hidden."""
        assert find(BENNETS, BENNETS.characters, TransformType.GENDER_SWAP) == {}

    def test_two_women_can_collide_with_each_other(self):
        """Lady Lucas and Miss Lucas both become Mr. Lucas; no man is involved."""
        analysis = cast(("Lady Lucas", Gender.FEMALE), ("Miss Lucas", Gender.FEMALE))
        found = find(analysis, women(analysis), TransformType.ALL_MALE)
        assert set(found) == {"Lady Lucas", "Miss Lucas"}
        assert found["Lady Lucas"]["candidate"] == "Mr. Lucas"
        assert found["Lady Lucas"]["clashes_with"] == "Miss Lucas"


class TestWhoIsLeftAlone:
    def test_a_character_with_a_given_name_is_fine(self):
        """Elizabeth Bennet can be renamed; she is not a title plus a surname."""
        analysis = cast(("Elizabeth Bennet", Gender.FEMALE), ("Mr. Bennet", Gender.MALE))
        assert find(analysis, women(analysis), TransformType.ALL_MALE) == {}

    def test_a_lone_title_with_nobody_to_clash_with_is_fine(self):
        analysis = cast(("Mrs. Annesley", Gender.FEMALE))
        assert find(analysis, women(analysis), TransformType.ALL_MALE) == {}

    def test_an_unrelated_surname_is_fine(self):
        analysis = cast(("Mrs. Bennet", Gender.FEMALE), ("Mr. Darcy", Gender.MALE))
        assert find(analysis, women(analysis), TransformType.ALL_MALE) == {}

    def test_a_three_word_name_is_not_a_bare_title(self):
        analysis = cast(("Lady Catherine de Bourgh", Gender.FEMALE), ("Mr. Bourgh", Gender.MALE))
        assert find(analysis, women(analysis), TransformType.ALL_MALE) == {}


class TestEdges:
    def test_an_empty_cast(self):
        empty = CharacterAnalysis(book_id="t", characters=[])
        assert find(empty, [], TransformType.ALL_MALE) == {}

    def test_a_transform_with_no_single_target_title(self):
        """gender_swap has no one destination title, so there is nothing to test."""
        assert find(BENNETS, BENNETS.characters, TransformType.GENDER_SWAP) == {}

    def test_a_character_never_clashes_with_themselves(self):
        analysis = cast(("Mr. Bennet", Gender.MALE))
        assert find(analysis, men(analysis), TransformType.ALL_MALE) == {}

    @pytest.mark.parametrize("title", ["Mrs.", "Miss", "Lady", "Ms.", "Mx."])
    def test_every_bare_title_is_recognised(self, title):
        analysis = cast((f"{title} Bennet", Gender.FEMALE), ("Mr. Bennet", Gender.MALE))
        found = find(analysis, women(analysis), TransformType.ALL_MALE)
        assert f"{title} Bennet" in found
