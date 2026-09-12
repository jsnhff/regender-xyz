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
and nothing anywhere objected.

Checking that turned up a second mechanism, in the engine rather than in the
suggestions. Deriving sub-entries from a supplied name took the first token
after the titles as the given name -- and "Noble", the word the nonbinary
variant itself introduces for Sir and Lady, was not in the title set. So
"Lady Catherine de Bourgh" -> "Noble Sydney de Bourgh" was read as the given
name "Noble", and emitted 'Catherine' -> 'Noble'. That removed the name from
all 132 places the book used it and left dialogue reading '"Certainly, Noble;
and it has the advantage..."'. Putting "Noble" in the title set fixes it at
source; the entries below keep the symptom from passing a gate again.

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
        assert check_rename(original, suggested), f"{original!r} -> {suggested!r} was accepted"

    def test_a_bare_title_is_named_as_such(self):
        assert check_rename("Catherine", "Noble") == "'Noble' is only a title, not a name"


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
            # Both of these lose a given name to a title, and both land on the
            # same "Noble de Bourgh" -- Lady Catherine and Sir Lewis, one name.
            # They were invisible while every de Bourgh read as a description.
            "Catherine de Bourgh",
            "Lewis de Bourgh",
            "Catherine",
            "Lewis",
        }


class TestTheAuditsWrongAnswers:
    """Twenty-one answers an adversarial audit found wrong, kept as a class.

    The first version of this gate guessed a name's shape from its punctuation
    and its title, and guessed wrong in both directions. It rejected correct
    renames -- dropping the suggestion so the reader never saw it -- and it
    accepted renames that merge two characters into one.

    The fix was to stop guessing: the cast says which tokens are surnames and
    which are given names, and a proposed name (which by definition is not in
    the cast) is read against the shape of the name it replaces.
    """

    @pytest.fixture(scope="class")
    def cast(self):
        """The real P&P cast, so the checks have the knowledge they need."""
        import json
        import pathlib

        from src.models.character import CharacterAnalysis
        from src.services.name_engine import cast_name_index

        path = pathlib.Path(
            "/Users/jasonhuff/regender-xyz/books/output/pride-and-prejudice/"
            "nonbinary_2026-09-11_23-16/characters.json"
        )
        if not path.exists():
            pytest.skip("the real cast is not on this machine")
        return cast_name_index(CharacterAnalysis.from_dict(json.loads(path.read_text())))

    def judge(self, cast, original, suggested):
        surnames, givens, reserved = cast
        return check_rename(
            original, suggested, surnames=surnames, givens=givens, reserved=reserved
        )

    @pytest.mark.parametrize(
        "original,suggested,why",
        [
            # Sir/Lady/Lord take a GIVEN name. Read as a surname, a correct
            # rename looked like a destroyed surname and was dropped.
            ("Sir William", "Noble Vivian", "Sir takes a given name"),
            ("Sir William", "Dame Wilhelmina", "the same, for all_female"),
            ("Lady Catherine", "Noble Sydney", "Lady takes a given name"),
            ("Lord Byron", "Noble Beverly", "Lord takes a given name"),
            # Elder and Younger are attested English surnames. Treating them as
            # surname qualifiers wherever they appeared rejected these.
            ("Elizabeth Elder", "Edmund Elder", "Elder is a surname"),
            ("Mary Younger", "Morgan Younger", "Younger is a surname"),
        ],
    )
    def test_the_false_positives_are_accepted(self, cast, original, suggested, why):
        problem = self.judge(cast, original, suggested)
        assert problem is None, f"{why}: wrongly refused with {problem!r}"

    @pytest.mark.parametrize(
        "original,suggested,why",
        [
            ("Elizabeth", "Jane", "Jane is another character: this merges them"),
            ("Elizabeth", "Bennet", "a live surname used as a given name"),
            ("Darcy", "Darcia", "invented, with the last letter traded"),
            # Malformed suggestions used to switch the whole check off, because
            # lowercase made them look like term substitutions.
            ("Elizabeth", "edward", "lowercase is not an exemption"),
            ("Elizabeth Bennet", "edward jones", "a surname destroyed in silence"),
            ("Catherine Bennet", "Young Meredith Bennet", "a stoplist word"),
            ("Elizabeth Bennet", "The Bennet child", "not a name"),
            ("Elizabeth Bennet", "Edward O'Hara", "an apostrophe is not an exemption"),
            ("Elizabeth Bennet", "O'Neill", "the surname is gone"),
            ("Lizzy", "teh", "a typo, applied to the whole book"),
            # A title or rank standing in for a name.
            ("Catherine", "Noble", "132 occurrences became a bare title"),
            ("Lewis", "Noble", "the same"),
        ],
    )
    def test_the_false_negatives_are_refused(self, cast, original, suggested, why):
        problem = self.judge(cast, original, suggested)
        assert problem is not None, f"{why}: wrongly accepted"

    @pytest.mark.parametrize(
        "original,suggested",
        [
            ("Sir William Lucas", "Noble William Lucas"),
            ("Mr. Fitzwilliam Darcy", "Mx. Fitzwilliam Darcy"),
            ("Mr. Jones", "Mx. Jones"),
            ("Mrs. Bennet", "Mx. Hilary Bennet"),
            ("Lady Anne Darcy", "Noble Dana Darcy"),
            ("Sir Lewis de Bourgh", "Noble Laurie de Bourgh"),
            ("Lady Lucas", "Noble Lucas"),
        ],
    )
    def test_the_cast_does_not_change_the_earlier_verdicts(self, cast, original, suggested):
        """Adding cast knowledge must not flip an answer that was already right."""
        assert (self.judge(cast, original, suggested) is None) == (
            check_rename(original, suggested) is None
        )


class TestTheCastIndex:
    """Surnames are settled before a bare token is read as a given name.

    Taking bare aliases at face value put "Darcy" in both sets, and a token that
    is both is ambiguous -- so every judgement about it was declined, and
    "Darcy" -> "Darcia" passed as a rename of nobody's given name.
    """

    def test_a_bare_alias_does_not_claim_a_known_surname(self):
        from src.models.character import Character, CharacterAnalysis, Gender
        from src.services.name_engine import cast_name_index

        cast = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Fitzwilliam Darcy",
                    gender=Gender.MALE,
                    pronouns={},
                    aliases=["Darcy", "Mr. Darcy"],
                )
            ],
        )
        surnames, givens, _ = cast_name_index(cast)
        assert "darcy" in surnames
        assert "darcy" not in givens
        assert "fitzwilliam" in givens


class TestWhatThisGateCannotKnow:
    """An honest boundary, recorded so nobody mistakes it for cover.

    Pratt and Chamberlayne are officers the book names only by surname. They
    look exactly like a character named only by a given name, and the cast
    cannot tell them apart: a lone token that never appears beside a surname is
    either one.

    The engine has the answer, because it asks -- a proposal can come back as
    {"original": "Pratt", "is_surname": true} and the name is then left alone.
    This function has no such signal, so it must not pretend to. Protection for
    those names lives on the engine side, which is why a suggestion rejected
    here falls through to the engine rather than being dropped outright.
    """

    def test_a_surname_only_character_is_not_caught_here(self):
        assert check_rename("Pratt", "Perry") is None
        assert check_rename("Chamberlayne", "Clare") is None

    def test_but_it_is_caught_once_the_cast_knows_it_is_a_surname(self):
        """Told the token is a surname, the gate does hold."""
        assert check_rename("Pratt", "Perry", surnames=frozenset({"pratt"}), givens=frozenset()), (
            "a known surname must not be renamed"
        )
