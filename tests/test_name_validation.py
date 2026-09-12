"""One bar for a rename, whichever path proposed it.

Two things decide names. The engine proposes and validates its own work. The
interface asks a model for suggestions, shows them to the reader, and whatever
the reader approves is passed to the engine as a base map -- where it wins, and
skips the engine's validation entirely. In the nonbinary edition the engine
proposed eight names and the final map had a hundred and two, so nearly every
name in the book came through the side that checked nothing except that the
suggestion differed from the original.

That is how these shipped:

    'Sir William Lucas'     -> 'Noble William Lucas'
    'Mr. Fitzwilliam Darcy' -> 'Mx. Fitzwilliam Darcy'

The honorific changed and the man's given name stayed, in a nonbinary edition,
and nothing anywhere objected. The same gap let the alias expansion put a bare
title where a given name had been -- 'Catherine' -> 'Noble' -- which removed the
name from all 132 places the book used it and left sentences reading
'"Certainly, Noble; and it has the advantage..."'.

check_rename is the shared bar. The hard part is not catching the failures; it
is staying silent on the entries that are correct, because a name map also
carries term substitutions that merely contain a surname.
"""

import pytest

from src.services.name_engine import check_rename, given_and_surname


class TestReadingAName:
    """A name has to be split before it can be judged."""

    @pytest.mark.parametrize(
        "name,given,surname",
        [
            ("Elizabeth Bennet", "Elizabeth", "Bennet"),
            ("Elizabeth", "Elizabeth", None),
            # A single token behind a title is a family name: "Mr. Jones" tells
            # us nothing about his given name.
            ("Mr. Jones", None, "Jones"),
            ("Mrs. Bennet", None, "Bennet"),
            ("Sir William Lucas", "William", "Lucas"),
            ("Lady Catherine de Bourgh", "Catherine", "de Bourgh"),
            # The particle belongs to the surname. Read as Given + Surname this
            # gives the given name "de".
            ("Miss de Bourgh", None, "de Bourgh"),
            # A qualifier disambiguates a surname; it does not follow a given name.
            ("Mrs. Wickham senior", None, "Wickham senior"),
            # "Noble" is the nonbinary title the pipeline itself introduces. Left
            # out of the title set it parsed as a given name, making the surname
            # "William Lucas".
            ("Noble William Lucas", "William", "Lucas"),
            ("Mx. Hilary Bennet", "Hilary", "Bennet"),
            ("Colonel Fitzwilliam", None, "Fitzwilliam"),
        ],
    )
    def test_splits(self, name, given, surname):
        assert given_and_surname(name) == (given, surname)


class TestTheReportedFailures:
    """The two the reader found, and the four found while checking them."""

    def test_a_title_swap_is_not_a_rename(self):
        problem = check_rename("Sir William Lucas", "Noble William Lucas")
        assert problem and "unchanged" in problem

    def test_it_catches_the_second_one_too(self):
        """Fitzwilliam is Darcy's given name, and just as masculine."""
        problem = check_rename("Mr. Fitzwilliam Darcy", "Mx. Fitzwilliam Darcy")
        assert problem and "unchanged" in problem

    @pytest.mark.parametrize(
        "original,suggested",
        [
            # A given name replaced by a bare title. 132 occurrences of
            # "Catherine" became "Noble".
            ("Catherine", "Noble"),
            ("Lewis", "Noble"),
            # And the same thing with the surname still attached.
            ("Anne Darcy", "Noble Darcy"),
            ("William Lucas", "Noble Lucas"),
        ],
    )
    def test_a_given_name_may_not_simply_vanish(self, original, suggested):
        problem = check_rename(original, suggested)
        assert problem, f"{original!r} -> {suggested!r} was accepted"
        assert "lost" in problem


class TestSurnamesAreFamilyNotGender:
    def test_a_changed_surname_is_refused(self):
        """The all-female edition lost roughly three hundred surnames this way:
        a rule for the nickname Lizzy sent Darcy to 'Fitzwillia'."""
        problem = check_rename("Lizzy Darcy", "Ned Fitzwillia")
        assert problem and "surname" in problem

    def test_a_dropped_surname_is_refused(self):
        problem = check_rename("Elizabeth Bennet", "Edward")
        assert problem and "surname" in problem


class TestWhatMustStillBeAllowed:
    """Every false positive here is a correct rename the reader never sees."""

    @pytest.mark.parametrize(
        "original,suggested",
        [
            # Ordinary renames, one per variant.
            ("Elizabeth Bennet", "Edward Bennet"),
            ("Lady Anne Darcy", "Noble Dana Darcy"),
            ("Sir Lewis de Bourgh", "Noble Laurie de Bourgh"),
            ("Lady Catherine de Bourgh", "Noble Sydney de Bourgh"),
            # A title swap is the whole answer when there is no given name to
            # change: "Mr. Jones" has only a surname.
            ("Mr. Jones", "Mx. Jones"),
            ("Miss King", "Mx. King"),
            ("Lady Lucas", "Noble Lucas"),
            # Giving a given name to someone who had none is the fix for two
            # characters collapsing into one person.
            ("Mrs. Bennet", "Mx. Hilary Bennet"),
            ("Mr. Gardiner", "Mx. Valentine Gardiner"),
        ],
    )
    def test_accepted(self, original, suggested):
        assert check_rename(original, suggested) is None, (
            f"{original!r} -> {suggested!r} was wrongly refused"
        )

    @pytest.mark.parametrize(
        "original,suggested",
        [
            # Not people. These are term substitutions that happen to contain a
            # surname, and reading them as Given + Surname refused nineteen
            # correct entries at once.
            ("Lucas boys", "Lucas children"),
            ("Lucas younger girls", "Lucas younger children"),
            ("The Butler", "The Steward"),
            ("The chambermaid", "The chamberperson"),
            ("Mr. Collins's father", "Mx. Collins's parent"),
            ("Wickham's Father", "Wickham's Parent"),
        ],
    )
    def test_term_substitutions_are_not_judged_as_names(self, original, suggested):
        assert check_rename(original, suggested) is None, (
            f"{original!r} -> {suggested!r} is a term substitution, not a rename"
        )


class TestAgainstTheShippedMap:
    """Measured against the real nonbinary edition, not a fixture.

    The gate is only useful if it is quiet where the edition was right. On the
    102-entry map it must object to the six known-bad entries and to nothing
    else; an earlier version objected to nineteen.
    """

    NAME_MAP = (
        "/Users/jasonhuff/regender-xyz/books/output/pride-and-prejudice/"
        "nonbinary_2026-09-11_23-16/name_map.json"
    )

    def test_exactly_the_known_bad_entries_are_refused(self):
        import json
        import pathlib

        path = pathlib.Path(self.NAME_MAP)
        if not path.exists():
            pytest.skip("the shipped nonbinary edition is not on this machine")

        name_map = json.loads(path.read_text())
        refused = {k for k, v in name_map.items() if check_rename(k, v)}
        assert refused == {
            "Sir William Lucas",
            "Mr. Fitzwilliam Darcy",
            "William Lucas",
            "Anne Darcy",
            "Catherine",
            "Lewis",
        }
