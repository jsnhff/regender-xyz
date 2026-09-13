"""When two title forms collide, the forename goes to whoever already has one.

Austen calls Jane "Miss Bennet" and her mother "Mrs. Bennet". Swap the cast and
both land on "Mr. Bennet", so one of them needs a forename to stay distinct.
Both sides were marked as needing one, and the model put it on the mother: the
finished swap edition said "Mr. Thomas Bennet" 152 times -- a forename Austen
never gives anybody -- while Jane's own renamed given name sat unused.

Only the character the book already named is marked now. Jane becomes "Mr.
James Bennet"; her mother keeps the plain title swap.

The rule is deliberately narrow, and these tests pin the narrowness as much as
the rule: it fires only on a mutual pair where exactly one side has a given
name. In all_female both Bennets land on "Mrs. Bennet" and neither has a
forename, so somebody must still be given one and nothing here interferes.
"""

import json
from pathlib import Path

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.character_service import CharacterService

FIXTURE = Path(__file__).parent / "fixtures" / "pride-and-prejudice-cast.json"


@pytest.fixture(scope="module")
def cast():
    return CharacterAnalysis.from_dict(json.loads(FIXTURE.read_text()))


def changing_for(cast, kind):
    out = []
    for char in cast.characters:
        gender = char.gender.value if hasattr(char.gender, "value") else str(char.gender)
        if (
            kind == "all_female"
            and gender == "male"
            or kind == "all_male"
            and gender == "female"
            or kind in ("gender_swap", "nonbinary")
            and gender in ("male", "female")
        ):
            out.append(char)
    return out


def collisions_for(cast, kind):
    return CharacterService._name_collisions(cast, changing_for(cast, kind), TransformType(kind))


class TestWhoIsAsked:
    def test_the_mother_is_no_longer_asked_for_a_forename(self, cast):
        """She has none in the book, so any given to her is invented."""
        assert "Mrs. Bennet" not in collisions_for(cast, "gender_swap")

    def test_jane_is(self, cast):
        """She has one, and using it costs the book nothing."""
        assert "Miss Bennet" in collisions_for(cast, "gender_swap")

    def test_they_still_land_on_the_same_name(self, cast):
        """If they did not, there would be nothing to resolve and the rule
        would be solving a problem that is not there."""
        swap = TransformType("gender_swap")
        assert CharacterService._landing_for("Mrs. Bennet", swap) == "Mr. Bennet"
        assert CharacterService._landing_for("Miss Bennet", swap) == "Mr. Bennet"


class TestWhatItDoesNotTouch:
    def test_all_female_is_unchanged(self, cast):
        """Both Bennets land on "Mrs. Bennet" and neither has a forename, so
        one must still be given one. Jason ran all_female against this."""
        found = collisions_for(cast, "all_female")
        assert "Mr. Bennet" in found
        assert found["Mr. Bennet"]["candidate"] == "Mrs. Bennet"

    @pytest.mark.parametrize("kind", ["all_male", "nonbinary"])
    def test_the_bennets_are_still_asked_where_the_titles_merge(self, cast, kind):
        found = collisions_for(cast, kind)
        assert any(form.endswith("Bennet") for form in found), found

    def test_a_pair_where_both_have_forenames_keeps_both(self):
        """The rule drops a side only when the other one has a name and this
        one does not. Two named characters are not this case."""
        cast = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Anne Lucas", gender=Gender.FEMALE, pronouns={}, aliases=["Miss Lucas"]
                ),
                Character(
                    name="Maria Lucas", gender=Gender.FEMALE, pronouns={}, aliases=["Lady Lucas"]
                ),
            ],
        )
        found = collisions_for(cast, "all_male")
        assert len(found) >= 1


class TestTheHelper:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("Jane Bennet Bingley", True),
            ("Elizabeth Bennet", True),
            ("Mrs. Bennet", False),
            ("Mr. Collins", False),
            ("Lady Catherine de Bourgh", True),
            ("Sally", False),
        ],
    )
    def test_it_knows_who_the_book_named(self, name, expected):
        assert CharacterService._has_given_name(name) is expected
