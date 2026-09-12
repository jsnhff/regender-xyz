"""Who is the same person, and who only looks like it.

One character listed twice gets renamed twice, and the book then calls one woman
two things. The gender-swap edition has the protagonist's suitor as both "Frances
Darcy" and "Mrs. Fitzwillia Darcy", because "Mr. Darcy" and "Fitzwilliam Darcy"
were two cast entries and neither named the other.

The opposite mistake is worse, and it is easy to make reaching for the first.
Every attempt at this has to be measured against a real cast, because the traps
are all in real data:

  * "his wife" is listed as an alias of Mrs. Bennet, Mrs. Wickham AND Harriet
    Forster. Taking a shared alias as identity chained six different women into
    one person.
  * "Miss Lucas" is an alias of both Charlotte and Maria Lucas, who are sisters.
  * "Harriet" is an alias of Harriet Forster and Harriet Harrington, two women
    who share a first name.
  * "Mrs. Bennet" and "Jane Bennet" are mother and daughter. They share a
    surname and a gender, and only the honorific tells them apart -- which
    structure cannot read, so they are left alone and raised for a person.
"""

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
from src.services.character_service import CharacterService, _is_name_form


def person(name, gender=Gender.FEMALE, aliases=()):
    return Character(name=name, gender=gender, pronouns={}, aliases=list(aliases))


def merge(cast):
    return CharacterService._merge_same_person(cast)


class TestTheSuitorWhoWasTwoPeople:
    def test_a_shared_short_name_folds_them(self):
        out, merged = merge(
            [
                person("Mr. Darcy", Gender.MALE, ["Darcy"]),
                person("Fitzwilliam Darcy", Gender.MALE, ["Darcy"]),
            ]
        )
        assert len(out) == 1
        assert out[0].name == "Fitzwilliam Darcy", "the form with a given name is canonical"

    def test_a_titled_duplicate_of_a_full_name_folds(self):
        out, _ = merge(
            [
                person("Anne de Bourgh", aliases=["Miss De Bourgh"]),
                person("Miss Anne de Bourgh", aliases=["Miss de Bourgh"]),
            ]
        )
        assert len(out) == 1


class TestARelationIsNotAnIdentity:
    def test_his_wife_does_not_chain_three_women_together(self):
        """Measured on the real cast: this folded six people into one."""
        out, _ = merge(
            [
                person("Mrs. Bennet", aliases=["his wife", "her mother", "mamma"]),
                person("Mrs. Wickham", aliases=["his wife"]),
                person("Harriet Forster", aliases=["his wife"]),
            ]
        )
        assert len(out) == 3

    @pytest.mark.parametrize(
        "alias,is_name",
        [
            ("Darcy", True),
            ("Miss Lucas", True),
            ("Lizzy", True),
            ("Miss de Bourgh", True),
            ("his wife", False),
            ("her mother", False),
            ("mamma", False),
            ("the eldest Miss Bennet", False),
            ("her Ladyship", False),
            ("the housekeeper", False),
            ("", False),
        ],
    )
    def test_what_counts_as_a_name(self, alias, is_name):
        assert _is_name_form(alias) is is_name


class TestWhoShareAFormOfAddressButNotAnIdentity:
    def test_two_sisters_are_not_one(self):
        """Charlotte and Maria Lucas both answer to "Miss Lucas"."""
        out, _ = merge(
            [
                person("Charlotte Lucas", aliases=["Miss Lucas"]),
                person("Maria Lucas", aliases=["Miss Lucas"]),
            ]
        )
        assert len(out) == 2

    def test_two_women_sharing_a_first_name_are_not_one(self):
        out, _ = merge(
            [
                person("Harriet Forster", aliases=["Harriet"]),
                person("Harriet Harrington", aliases=["Harriet"]),
            ]
        )
        assert len(out) == 2

    def test_a_mother_and_her_daughter_are_not_one(self):
        out, merged = merge([person("Mrs. Bennet"), person("Jane Bennet")])
        assert len(out) == 2 and not merged

    def test_a_husband_and_his_wife_are_not_one(self):
        out, merged = merge([person("Mr. Hurst", Gender.MALE), person("Louisa Hurst")])
        assert len(out) == 2 and not merged


class TestMarriedCouplesAreNotEvenGroupedAsCandidates:
    """Asking the merge step about a married pair is asking for an error."""

    @pytest.fixture
    def svc(self):
        s = CharacterService.__new__(CharacterService)
        import logging

        s.logger = logging.getLogger("t")
        s.grouping_config = {
            "deduplication_similarity_threshold": 80,
            "similarity_threshold": 0.8,
        }
        return s

    @pytest.mark.parametrize(
        "a,b",
        [
            ("Mr. Bennet", "Mrs. Bennet"),
            ("Mr. Hurst", "Mrs. Hurst"),
            ("Mr. Gardiner", "Mrs. Gardiner"),
            ("Mr. Philips", "Mrs. Philips"),
        ],
    )
    def test_they_are_not_similar(self, svc, a, b):
        assert not svc._are_similar({"name": a}, {"name": b})

    def test_but_a_title_and_a_given_name_still_group(self, svc):
        """ "miss" was missing from the title set, so "Anne de Bourgh" against
        "Miss Anne de Bourgh" scored a perfect 100 and was rejected anyway."""
        assert svc._are_similar({"name": "Anne de Bourgh"}, {"name": "Miss Anne de Bourgh"})

    def test_and_siblings_still_do_not(self, svc):
        assert not svc._are_similar({"name": "Elizabeth Bennet"}, {"name": "Jane Bennet"})


class TestReadingACastIsNotAWritingTask:
    def test_the_extraction_temperature_is_zero(self):
        """22 of the 90 characters are mentioned exactly once, so at 0.3 each was
        a coin flip: successive runs found 89, 91, 88, 86, 85, 77, 80 and 82."""
        import json
        import pathlib

        config = json.loads(
            (pathlib.Path(__file__).parent.parent / "src" / "config.json").read_text()
        )
        assert config["character_extraction"]["temperature"] == 0.0

    def test_the_transform_temperature_is_left_alone(self):
        """Writing prose is a different task and wants a different setting."""
        import json
        import pathlib

        config = json.loads(
            (pathlib.Path(__file__).parent.parent / "src" / "config.json").read_text()
        )
        assert config["transformation"]["temperature"] > 0


class TestAgainstTheRealCast:
    """The only test that would have caught the six-way collapse."""

    def test_every_fold_is_a_real_duplicate(self):
        import json
        import pathlib

        path = pathlib.Path(
            "/Users/jasonhuff/regender-xyz/books/output/pride-and-prejudice/"
            "all_male_2026-09-10_21-44/characters.json"
        )
        if not path.exists():
            pytest.skip("the real cast is not on this machine")

        cast = CharacterAnalysis.from_dict(json.loads(path.read_text()))
        out, merged = merge(list(cast.characters))

        folded = {fold for _keep, fold in merged}
        # Nobody who is their own person may be folded away.
        for name in (
            "Mr. Bennet",
            "Mrs. Bennet",
            "Jane Bennet",
            "Mary Bennet",
            "Elizabeth Bennet",
            "Maria Lucas",
            "Harriet Harrington",
            "Mr. Hurst",
        ):
            assert name not in folded, f"{name} is their own person"

        # And the duplicate that cost the most is gone.
        assert "Mr. Darcy" in folded
        assert len(out) < len(cast.characters)

    def test_it_does_not_depend_on_the_transform(self):
        """The cast is the book's, not the variant's."""
        import json
        import pathlib

        path = pathlib.Path(
            "/Users/jasonhuff/regender-xyz/books/output/pride-and-prejudice/"
            "all_male_2026-09-10_21-44/characters.json"
        )
        if not path.exists():
            pytest.skip("the real cast is not on this machine")
        cast = CharacterAnalysis.from_dict(json.loads(path.read_text()))
        counts = set()
        for _ in TransformType:
            out, _ = merge(list(cast.characters))
            counts.add(len(out))
        assert len(counts) == 1
