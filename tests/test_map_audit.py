"""Some faults are only visible in the whole map.

Every entry in the shipped maps defends itself. The damage is in how they sit
together, and nothing was looking at that.

One character, several names. Ten source given names carry two or more targets
across the four editions: Charlotte is "Courtney" 97 times and "Carol" 71 times
in the same book; Mary is "Francis" 42 times and "Morgan" twice; the all-male
edition gives one girl three names, Catherine to Cuthbert, Kitty to Kit, and
Catherine Bennet to Christopher Bennet.

Two characters, one name. Eight target given names are claimed by two different
people: "Hilary" is 461 mentions shared between Mr. Bennet and Mr. Collins, and
"Aubrey" makes Elizabeth Bennet and Anne de Bourgh the same person across 1057
occurrences.

The first also hides the second. Asked whether a rename landed, quality control
takes the best match across all of a name's targets -- so once a name has two,
a target that is also a common word reports success everywhere. "Catherine"
occurs 132 times in the source and 0 times in the nonbinary edition, and QC
raised nothing at any severity.
"""

import pytest

from src.models.character import Character, CharacterAnalysis, Gender
from src.services.name_engine import audit_name_map


def cast(*names):
    return CharacterAnalysis(
        book_id="t",
        characters=[
            Character(name=n, gender=Gender.FEMALE, pronouns={}, aliases=list(a))
            for n, *a in (n if isinstance(n, tuple) else (n,) for n in names)
        ],
    )


class TestOneCharacterSeveralNames:
    """One person under two names. Identity comes from the cast, because two
    different Annes are two people and may have two names -- Austen's own cast
    has two Marys and three Williams."""

    def test_two_names_for_one_person_is_reported(self):
        cast = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Charlotte Collins",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Charlotte Lucas"],
                )
            ],
        )
        problems = audit_name_map(
            {
                "Charlotte Lucas": "Courtney Lucas",
                "Charlotte Collins": "Carol Collins",
            },
            cast,
        )
        assert any("two people, one name" in p or "several names" in p for p in problems), problems

    def test_two_different_people_sharing_a_first_name_are_fine(self):
        """Mary Bennet and Mary King are two women and get two names."""
        problems = audit_name_map(
            {"Mary Bennet": "Martin Bennet", "Mary King": "Matthew King"},
            cast("Mary Bennet", "Mary King"),
        )
        assert problems == [], problems

    def test_a_nickname_is_not_a_contradiction(self):
        """Kitty and Catherine Bennet are one girl; "Kit" is a short form of
        "Christopher" and not a second name for her."""
        people = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Catherine Bennet",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Kitty", "Kitty Bennet"],
                )
            ],
        )
        problems = audit_name_map({"Kitty": "Kit", "Kitty Bennet": "Christopher Bennet"}, people)
        assert not [p for p in problems if "several names" in p], problems


class TestTwoCharactersOneName:
    """Two people a reader could not tell apart. A shared given name is only
    confusing when the surname matches too."""

    def test_the_same_full_name_for_two_people_is_reported(self):
        problems = audit_name_map(
            {"Harriet Forster": "Hilary Forster", "Henrietta Forster": "Hilary Forster"},
            cast("Harriet Forster", "Henrietta Forster"),
        )
        assert any("2 different characters" in p for p in problems), problems

    def test_a_shared_given_name_across_surnames_is_fine(self):
        """Christopher Bingley and Christopher Bennet are two men, as the book
        already has two Marys."""
        problems = audit_name_map(
            {"Caroline Bingley": "Christopher Bingley", "Kitty Bennet": "Christopher Bennet"},
            cast("Caroline Bingley", "Kitty Bennet"),
        )
        assert not [p for p in problems if "different characters" in p], problems

    def test_one_person_under_two_forms_sharing_a_target_is_fine(self):
        """ "Kitty Bennet" and "Catherine Bennet" are one girl, so of course they
        map to the same name. Reporting that is the opposite of the truth."""
        people = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Catherine Bennet",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Kitty Bennet"],
                )
            ],
        )
        problems = audit_name_map(
            {"Catherine Bennet": "Christopher Bennet", "Kitty Bennet": "Christopher Bennet"},
            people,
        )
        assert not [p for p in problems if "different characters" in p], problems


class TestPerEntryFaultsAreStillReported:
    @pytest.mark.parametrize(
        "key,value",
        [
            ("Catherine", "Noble"),
            ("Sir William Lucas", "Noble William Lucas"),
            ("Catherine de Bourgh", "Noble de Bourgh"),
        ],
    )
    def test_the_entry_is_named(self, key, value):
        problems = audit_name_map({key: value}, cast("Catherine de Bourgh"))
        assert any(key in p for p in problems)


class TestItStaysQuietWhereTheMapIsRight:
    def test_term_substitutions_are_not_judged(self):
        problems = audit_name_map(
            {
                "Lucas boys": "Lucas children",
                "The chambermaid": "The chamberperson",
                "Wickham's Father": "Wickham's Parent",
                "Mr. Jones": "Mx. Jones",
                "Mrs. Bennet": "Mx. Hilary Bennet",
            },
            cast("Mr. Jones", "Mrs. Bennet"),
        )
        assert problems == []

    def test_a_nobiliary_particle_is_a_name_not_a_defect(self):
        """ "Louise de Bourgh" is a name; reading its "de" as a fault refused
        eight correct renames across the shipped editions."""
        problems = audit_name_map(
            {"Lewis de Bourgh": "Louise de Bourgh"},
            cast("Lewis de Bourgh"),
        )
        assert problems == []


class TestAgainstTheShippedEditions:
    """Measured, not fixtured: the audit must find what was actually there, and
    stay quiet about what was not."""

    def test_the_nonbinary_edition(self):
        import json
        import pathlib

        base = pathlib.Path(
            "/Users/jasonhuff/regender-xyz/books/output/pride-and-prejudice/"
            "nonbinary_2026-09-11_23-16"
        )
        if not (base / "name_map.json").exists():
            pytest.skip("the shipped nonbinary edition is not on this machine")

        name_map = json.loads((base / "name_map.json").read_text())
        characters = CharacterAnalysis.from_dict(json.loads((base / "characters.json").read_text()))
        problems = audit_name_map(name_map, characters)

        # Elizabeth Bennet and Anne de Bourgh were both called Aubrey, across
        # 1057 occurrences, and Sir William kept a man's given name.
        assert any("aubrey" in p for p in problems), problems
        assert any("Sir William Lucas" in p for p in problems), problems
        # And the report stays short enough to act on.
        assert len(problems) <= 14, problems

    def test_the_gender_swap_the_reader_ran(self):
        """Three findings, and the one that matters is a name that is not a
        name: Darcy was called "Fitzwillia" 222 times."""
        import json
        import pathlib

        base = pathlib.Path(
            "/Users/jasonhuff/regender-xyz/books/output/pride-and-prejudice/"
            "gender_swap_2026-09-12_14-37"
        )
        if not (base / "name_map.json").exists():
            pytest.skip("that edition is not on this machine")

        name_map = json.loads((base / "name_map.json").read_text())
        characters = CharacterAnalysis.from_dict(json.loads((base / "characters.json").read_text()))
        problems = audit_name_map(name_map, characters)
        assert any("Fitzwillia" in p for p in problems), problems
        assert len(problems) <= 5, problems
