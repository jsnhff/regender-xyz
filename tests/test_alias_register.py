"""Keep the honorifics, and see the collisions that make people lose them.

Austen's register lives in her forms of address. The alias expansion had been
turning them into bare given names, and the shipped editions show what that
costs, measured against the source:

    "Miss Bennet"   59 -> 0     ("Jesse Bennet" 44)
    "Mrs. Hurst"    21 -> 0     ("Leslie Hurst" 22)
    "Mr. Collins"  145 -> 0     ("Hilary Collins" 242, 8 "Mx. Collins")

    "danced only once with Mrs. Hurst and once with Miss Bingley"
 -> "once with Leslie Hurst and once with Jocelyn Bingley"

The same entries also wrote renames the name engine had explicitly declined in
order to keep two characters apart: 313 source occurrences in the all-female
edition, past a refusal recorded in that run's own report, with no flag.

Two more shapes went the same way. A relation is not a name -- "mamma" was
mapped to "Mx. Hilary Bennet", so five passages have children addressing their
mother as '"Oh, Mx. Hilary Bennet,"'. And a title in front of a full name made
a nickname into a formal address: with the target "Dame Louisa de Bourgh", the
alias "Lew" turned '"Come, Lew, you must dance."' into '"Come, Dame Louisa de
Bourgh, you must dance."'

Refusing these puts the work where it belongs. The term map moves the title and
the surname survives, so "Miss Bennet" becomes "Mr. Bennet". Where transforming
the title really would merge two people, that is a collision, and a collision
is answered once by giving one of them a given name -- not papered over by
renaming the form of address.
"""

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.character_service import CharacterService
from src.services.transform_service import TransformService


@pytest.fixture
def svc():
    return TransformService.__new__(TransformService)


class TestAFormOfAddressIsNotANickname:
    @pytest.mark.parametrize(
        "alias",
        [
            "Miss Bennet",
            "Mrs. Hurst",
            "Mr. Collins",
            "Mrs. Collins",
            "Mr. Bingley",
            "Mr. Wickham",
            "Miss Elizabeth",
            "Miss Eliza",
            "Miss Lucas",
            "Colonel Forster",
            "Lady Lucas",
            "Noble Lucas",
        ],
    )
    def test_it_never_becomes_a_rename(self, svc, alias):
        assert svc._unsafe_alias(alias, "Charles Collins")

    @pytest.mark.parametrize("alias", ["Lizzy", "Eliza", "Kitty", "Jane", "Charlotte"])
    def test_a_nickname_still_does(self, svc, alias):
        assert not svc._unsafe_alias(alias, "Edmund")


class TestARelationIsNotAName:
    @pytest.mark.parametrize(
        "alias",
        [
            "mamma",
            "papa",
            "sister-in-law",
            "brother Gardiner",
            "old Wickham",
            "her Ladyship",
            "my uncle Philips",
            "the housekeeper",
            "her husband",
            "their father",
        ],
    )
    def test_it_never_becomes_a_rename(self, svc, alias):
        assert svc._unsafe_alias(alias, "Mx. Hilary Bennet")


class TestANicknameIsNotAFormalAddress:
    """_given_name used to hand back the whole titled name."""

    @pytest.mark.parametrize(
        "target,expected",
        [
            ("Dame Louisa de Bourgh", "Louisa"),
            ("Lord Andrew Darcy", "Andrew"),
            ("Noble Sydney de Bourgh", "Sydney"),
            ("Mx. Hilary Bennet", "Hilary"),
            ("Edward Bennet", "Edward"),
            # Nothing to take: a bare surname behind a title, or behind a
            # particle, leaves the name as it stands.
            ("Mr. King", "Mr. King"),
            ("Noble de Bourgh", "Noble de Bourgh"),
            ("Edward", "Edward"),
        ],
    )
    def test_the_title_is_skipped_only_when_a_name_is_behind_it(self, svc, target, expected):
        assert TransformService._given_name(target) == expected


class TestThePhraseStillComesOutRight:
    """Refusing the entry is only safe if nothing is left behind."""

    def test_a_titled_given_name_is_carried_by_the_name_inside_it(self, svc):
        cast = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Elizabeth Bennet",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Miss Elizabeth", "Miss Bennet", "Lizzy"],
                )
            ],
        )
        expanded = svc._expand_name_map_with_aliases({"Elizabeth Bennet": "Edmund Bennet"}, cast)
        assert "Miss Elizabeth" not in expanded
        assert "Miss Bennet" not in expanded
        assert expanded["Elizabeth"] == "Edmund"
        assert expanded["Lizzy"] == "Edmund"

        assert svc._apply_name_map("Miss Elizabeth called.", expanded) == "Miss Edmund called."
        # And the surname form is left for the term map, which keeps the title.
        assert svc._apply_name_map("Miss Bennet called.", expanded) == "Miss Bennet called."
        assert (
            svc._apply_term_map("Miss Bennet called.", TransformType.ALL_MALE)
            == "Mr. Bennet called."
        )


class TestTheCollisionsThatJustifyIt:
    """Refusing the alias is only correct if the merge is caught instead."""

    @pytest.fixture
    def cast(self):
        return CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Charlotte Collins",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Mrs. Collins", "Miss Lucas"],
                ),
                Character(
                    name="William Collins",
                    gender=Gender.MALE,
                    pronouns={},
                    aliases=["Mr. Collins"],
                ),
            ],
        )

    def test_a_form_of_address_is_examined_not_only_a_cast_name(self, cast):
        """Charlotte is listed under her full name, so nothing titled was ever
        looked at for her -- yet the book calls her "Mrs. Collins" forty times,
        and in an all-male edition that lands exactly on her husband."""
        changing = [c for c in cast.characters if c.gender.value == "female"]
        collisions = CharacterService._name_collisions(cast, changing, TransformType.ALL_MALE)
        assert "Mrs. Collins" in collisions
        assert collisions["Mrs. Collins"]["candidate"] == "Mr. Collins"

    def test_gender_swap_is_checked_at_all(self, cast):
        """It returned nothing for the swap: 73 characters changing, no check.
        The destination title is per character there, not one for the book."""
        siblings = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(name="Mrs. Bennet", gender=Gender.FEMALE, pronouns={}),
                Character(name="Miss Bennet", gender=Gender.FEMALE, pronouns={}),
            ],
        )
        collisions = CharacterService._name_collisions(
            siblings, list(siblings.characters), TransformType.GENDER_SWAP
        )
        # Miss -> Mr. and Mrs. -> Mr.: both land on the same man.
        assert collisions
        assert all(info["candidate"] == "Mr. Bennet" for info in collisions.values())

    @pytest.mark.parametrize(
        "transform",
        [
            TransformType.ALL_MALE,
            TransformType.ALL_FEMALE,
            TransformType.NONBINARY,
            TransformType.GENDER_SWAP,
        ],
    )
    def test_every_transform_gets_an_answer(self, cast, transform):
        changing = [c for c in cast.characters if c.gender.value in ("male", "female")]
        result = CharacterService._name_collisions(cast, changing, transform)
        assert isinstance(result, dict)
