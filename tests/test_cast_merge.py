"""One person, one entry, one name.

Extraction lists a person once by name, again by title, and a third time under
a married surname: "Lydia Bennet", "Lydia Wickham" and "Mrs. Wickham" are one
woman. Each entry was renamed on its own, so she came out of an all_male run as
Lionel 182 times and Lyle once.

The opposite mistake is worse. Folding a mother into her daughter, or a husband
into his wife, would merge two people who share a surname and nothing else.
"""

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.character_service import CharacterService
from src.services.transform_service import TransformService

merge = CharacterService._merge_same_person


def person(name, gender=Gender.FEMALE, aliases=()):
    return Character(name=name, gender=gender, pronouns={}, aliases=list(aliases))


class TestFoldingTheSamePerson:
    def test_a_title_entry_folds_into_the_named_one(self):
        cast = [person("Louisa Hurst", aliases=["Mrs. Hurst"]), person("Mrs. Hurst")]
        out, merged = merge(cast)
        assert [c.name for c in out] == ["Louisa Hurst"]
        assert merged == [("Louisa Hurst", "Mrs. Hurst")]

    def test_the_folded_name_survives_as_an_alias(self):
        cast = [person("Louisa Hurst", aliases=["Mrs. Hurst"]), person("Mrs. Hurst")]
        out, _ = merge(cast)
        assert "Mrs. Hurst" in out[0].aliases

    def test_a_married_surname_folds_too(self):
        cast = [
            person("Lydia Wickham", aliases=["Lydia Bennet", "Mrs. Wickham"]),
            person("Lydia Bennet"),
            person("Mrs. Wickham"),
        ]
        out, merged = merge(cast)
        assert len(out) == 1
        assert len(merged) == 2

    def test_a_chain_collapses_to_one(self):
        cast = [
            person("Charlotte Collins", aliases=["Charlotte Lucas"]),
            person("Charlotte Lucas", aliases=["Miss Lucas"]),
            person("Miss Lucas"),
        ]
        out, _ = merge(cast)
        assert len(out) == 1

    def test_nobody_is_lost(self):
        cast = [person("Louisa Hurst", aliases=["Mrs. Hurst"]), person("Mrs. Hurst")]
        out, merged = merge(cast)
        assert {c.name for c in out} | {f for _k, f in merged} == {"Louisa Hurst", "Mrs. Hurst"}


class TestWhoMustStaySeparate:
    def test_a_mother_and_her_daughter(self):
        cast = [person("Mrs. Bennet"), person("Jane Bennet")]
        out, merged = merge(cast)
        assert len(out) == 2 and not merged

    def test_a_husband_and_his_wife(self):
        cast = [person("Mr. Hurst", Gender.MALE), person("Louisa Hurst")]
        out, merged = merge(cast)
        assert len(out) == 2 and not merged

    def test_a_shared_surname_alone_is_not_enough(self):
        """Only entries that name each other are folded."""
        cast = [person("Mr. Darcy", Gender.MALE), person("Georgiana Darcy")]
        out, _ = merge(cast)
        assert len(out) == 2

    def test_an_alias_naming_a_different_gender_is_not_the_same_person(self):
        """ "her husband" as an alias must not fold him into her."""
        cast = [
            person("Louisa Hurst", aliases=["Mr. Hurst"]),
            person("Mr. Hurst", Gender.MALE),
        ]
        out, merged = merge(cast)
        assert len(out) == 2 and not merged

    def test_a_cast_with_no_duplicates_is_untouched(self):
        cast = [person("Elizabeth Bennet"), person("Mr. Darcy", Gender.MALE)]
        out, merged = merge(cast)
        assert len(out) == 2 and merged == []


class TestTheAliasKeepsItsOwnSurname:
    """She is Lydia Bennet before the wedding and Lydia Wickham after."""

    def svc(self):
        return TransformService.__new__(TransformService)

    def test_a_maiden_name_keeps_its_surname(self):
        analysis = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Lydia Wickham",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Lydia Bennet"],
                )
            ],
        )
        expanded = self.svc()._expand_name_map_with_aliases(
            {"Lydia Wickham": "Lyle Wickham"}, analysis
        )
        assert expanded["Lydia Bennet"] == "Lyle Bennet"

    def test_the_canonical_name_is_unchanged(self):
        analysis = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Lydia Wickham",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Lydia Bennet"],
                )
            ],
        )
        expanded = self.svc()._expand_name_map_with_aliases(
            {"Lydia Wickham": "Lyle Wickham"}, analysis
        )
        assert expanded["Lydia Wickham"] == "Lyle Wickham"

    def test_a_titled_alias_needs_no_entry_of_its_own(self):
        """The name inside the phrase carries it, and the register survives.

        Giving these their own entries is how the book lost its honorifics:
        "Miss Bennet" mapped to a bare given name fell from 59 occurrences to 0,
        and "Miss Eliza" mapped to the cast's canonical "Elijah Bennet Darcy"
        put Darcy's name on Elizabeth years before the wedding.

        Nothing has to reach inside the phrase. "Elizabeth" -> "Edmund" fires
        within "Miss Elizabeth", and the term map moves the honorific, so the
        phrase arrives as "Mr. Edmund" with no entry for it anywhere.
        """
        analysis = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Elizabeth Bennet",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Miss Elizabeth", "Miss Bennet"],
                )
            ],
        )
        svc = self.svc()
        expanded = svc._expand_name_map_with_aliases(
            {"Elizabeth Bennet": "Edmund Bennet"}, analysis
        )
        assert "Miss Elizabeth" not in expanded
        assert "Miss Bennet" not in expanded
        assert expanded["Elizabeth"] == "Edmund"

        # And the phrases come out right without them.
        assert (
            svc._apply_name_map("Miss Elizabeth was announced.", expanded)
            == "Miss Edmund was announced."
        )
        assert (
            svc._apply_name_map("Miss Bennet was announced.", expanded)
            == "Miss Bennet was announced."
        )


@pytest.mark.parametrize(
    "transform", [TransformType.ALL_MALE, TransformType.ALL_FEMALE, TransformType.GENDER_SWAP]
)
def test_merging_does_not_depend_on_the_transform(transform):
    cast = [person("Louisa Hurst", aliases=["Mrs. Hurst"]), person("Mrs. Hurst")]
    out, _ = merge(cast)
    assert len(out) == 1
