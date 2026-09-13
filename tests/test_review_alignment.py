"""Show the same passage on both lines, and catch a mangled name.

The reader was shown two review cards whose "was" line was identical and whose
"now" line was four hundred characters away in the same paragraph. The word diff
then lit up nearly every word, because the two lines were not the same sentence.

The cause is specific to a bidirectional swap. In that paragraph "Mrs. Hurst"
correctly became "Mr. Hurst" while a real "Mr. Hurst" was missed, so the output
holds the phrase twice and the source holds it once. Anchoring the source
excerpt on the term meant both findings landed on that single occurrence.

The surrounding words are the better anchor, because they are what did not
change.

Reading those cards once they lined up showed all eleven were correct
transformations -- and showed two faults nothing had reported: Darcy was called
"Fitzwillia" 222 times, and Mr. Collins lost his given name.
"""

import pytest

from src.services.name_engine import _is_invented, cast_name_index, check_rename
from src.services.qc_service import _aligned_position, _source_anchor

SOURCE = (
    "The day passed much as the day before had done. Mrs. Hurst and Miss Bingley had "
    "spent some hours of the morning with the invalid. Mr. Darcy was writing, and Miss "
    "Bingley was watching. Mr. Hurst and Mr. Bingley were at piquet, and Mrs. Hurst was "
    "observing their game."
)
OUTPUT = (
    "The day passed much as the day before had done. Mr. Hurst and Christopher Bingley "
    "had spent some hours of the morning with the invalid. Fitzwillia Darcy was writing, "
    "and Christopher Bingley was watching. Mr. Hurst and Clara Bingley were at piquet, "
    "and Mr. Hurst was observing their game."
)


class TestTheTwoLinesAreTheSamePassage:
    def test_each_occurrence_finds_its_own_source(self):
        first = OUTPUT.index("Mr. Hurst")
        second = OUTPUT.rindex("Mr. Hurst")
        assert first != second

        a = _source_anchor(SOURCE, OUTPUT, "Mr. Hurst", first)
        b = _source_anchor(SOURCE, OUTPUT, "Mr. Hurst", second)
        assert a != b, "two occurrences must not resolve to one place"

        # The first came from "Mrs. Hurst and Miss Bingley", the second from
        # "and Mrs. Hurst was observing".
        assert "Miss Bingley" in SOURCE[a : a + 60]
        assert "observing" in SOURCE[b : b + 60]

    def test_the_anchor_lands_near_the_counterpart(self):
        second = OUTPUT.rindex("Mr. Hurst")
        anchor = _source_anchor(SOURCE, OUTPUT, "Mr. Hurst", second)
        assert "Mrs. Hurst" in SOURCE[max(0, anchor - 10) : anchor + 20]

    def test_a_rewritten_passage_falls_back_rather_than_guessing(self):
        """A weak match means the sentence was replaced, not adjusted."""
        assert _aligned_position("nothing alike at all here", "completely different words", 5) == -1

    @pytest.mark.parametrize("text", ["", "   "])
    def test_empty_input_is_not_an_error(self, text):
        """Nothing to match against is "no answer", which the caller reads as
        a signal to fall back rather than as position zero."""
        assert _aligned_position(text, OUTPUT, 0) in (0, -1)
        assert _aligned_position(SOURCE, text, 0) in (0, -1)
        # And the caller always gets a usable number back.
        assert _source_anchor(text, OUTPUT, "Mr. Hurst", 0) >= 0


class TestAMangledName:
    """ "Fitzwillia" is "Fitzwilliam" with its last letter removed. It is not a
    name in any language and it was in the map, so Darcy was called it 222 times
    in a finished edition."""

    @pytest.mark.parametrize(
        "original,target",
        [
            ("Fitzwilliam", "Fitzwillia"),
            ("Elizabeth", "Elizabet"),
            ("Darcy", "Darcia"),
            ("Fitzwilliam", "Fitzwilliama"),
        ],
    )
    def test_it_is_refused(self, original, target):
        assert _is_invented(original, target)

    @pytest.mark.parametrize(
        "original,target",
        [
            # Real short forms, which share a prefix and must survive.
            ("Kitty", "Kit"),
            ("Elizabeth", "Eliza"),
            ("Edward", "Ned"),
            # Real different names.
            ("Jane", "James"),
            ("Catherine", "Christopher"),
            ("Mary", "Martin"),
            ("Charlotte", "Chester"),
            ("Lydia", "Lionel"),
        ],
    )
    def test_a_real_name_is_not(self, original, target):
        assert not _is_invented(original, target)

    def test_the_map_entry_that_shipped(self):
        assert check_rename("Mr. Fitzwilliam Darcy", "Mrs. Fitzwillia Darcy")


class TestADescriptionIsNotEvidenceAboutAName:
    """The cast carried "my sweetest Lizzy" and "Dearest Jane" as aliases. Read
    as Given + Surname they filed Lizzy and Jane as family names, so the correct
    rename of the given name Jane reported a destroyed surname."""

    def test_an_endearment_does_not_teach_the_index_a_surname(self):
        from src.models.character import Character, CharacterAnalysis, Gender

        cast = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Jane Bennet",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Dearest Jane", "my sweetest Lizzy", "dear Lizzy"],
                )
            ],
        )
        surnames, givens, _ = cast_name_index(cast)
        assert "jane" not in surnames
        assert "lizzy" not in surnames
        assert "bennet" in surnames

    def test_and_so_the_rename_reads_correctly(self):
        from src.models.character import Character, CharacterAnalysis, Gender

        cast = CharacterAnalysis(
            book_id="t",
            characters=[
                Character(
                    name="Jane Bennet",
                    gender=Gender.FEMALE,
                    pronouns={},
                    aliases=["Dearest Jane", "Jane"],
                )
            ],
        )
        surnames, givens, reserved = cast_name_index(cast)
        assert check_rename("Jane", "James", surnames=surnames, givens=givens) is None
