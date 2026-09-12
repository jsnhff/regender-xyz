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
    def test_two_targets_for_one_given_name_is_reported(self):
        problems = audit_name_map(
            {
                "Charlotte Lucas": "Courtney Lucas",
                "Charlotte Collins": "Carol Collins",
            },
            cast("Charlotte Lucas", "Charlotte Collins"),
        )
        assert any("renamed 2 different ways" in p and "charlotte" in p for p in problems)

    def test_three_are_reported_as_three(self):
        problems = audit_name_map(
            {
                "Catherine Bennet": "Christopher Bennet",
                "Catherine de Bourgh": "Cuthbert de Bourgh",
                "Catherine Long": "Charles Long",
            },
            cast("Catherine Bennet", "Catherine de Bourgh", "Catherine Long"),
        )
        assert any("renamed 3 different ways" in p for p in problems)

    def test_one_target_everywhere_is_silent(self):
        problems = audit_name_map(
            {
                "Charlotte Lucas": "Carol Lucas",
                "Charlotte Collins": "Carol Collins",
            },
            cast("Charlotte Lucas", "Charlotte Collins"),
        )
        assert not [p for p in problems if "different ways" in p]


class TestTwoCharactersOneName:
    def test_a_shared_target_is_reported(self):
        problems = audit_name_map(
            {
                "Harriet Forster": "Hilary Forster",
                "William Collins": "Hilary Collins",
            },
            cast("Harriet Forster", "William Collins"),
        )
        assert any("2 different characters" in p and "hilary" in p for p in problems)

    def test_distinct_targets_are_silent(self):
        problems = audit_name_map(
            {
                "Harriet Forster": "Evelyn Forster",
                "William Collins": "Hilary Collins",
            },
            cast("Harriet Forster", "William Collins"),
        )
        assert not [p for p in problems if "different characters" in p]


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
    """Measured, not fixtured: the audit must find what was actually there."""

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

        multi = [p for p in problems if "different ways" in p]
        shared = [p for p in problems if "different characters" in p]
        # The audit that found these counted ten and eight; "william" appears in
        # both lists, which is why the shared count differs by the overlap.
        assert len(multi) >= 9, multi
        assert len(shared) >= 4, shared
        assert any("charlotte" in p for p in multi)
        assert any("hilary" in p for p in shared)
        assert any("aubrey" in p for p in shared)
