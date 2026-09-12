"""An oath is not a peerage, and a repair must be able to fire.

Two things, related by the same mechanism.

"Oh, Lord!" is swearing, not a title. Only "Good Lord" and "Lord bless" were
held back from the title map, so the bare exclamation went through it: "Lord!
how I laughed!" came out "Noble! how I laughed!" in the nonbinary edition and
would have been "Lady!" in the others. Every "Lord!" oath in Pride and Prejudice
is Lydia or Mrs. Bennet, so the replacement has to keep that register -- loud,
unguarded, and hers. Austen supplies it: "Good gracious" is Mrs. Bennet's own,
five times in this book, and she stacks them: "Good gracious! Lord bless me!
only think! dear me!" "Heaven" carries the blessing, seven times.

And the repair rules could not run at all. The residual mask asks whether a word
is identical to its source counterpart, so the net never undoes correct model
work -- but a coined word is by definition not identical to its source, so every
rule whose job was to repair one was structurally dead. "nibbling" -> "nibling"
was written and commented as an LLM typo correction and could never correct an
LLM typo: the shipped edition has 30 of one beside 34 of the other, and
"Ladyship" came back in six spellings of which the deterministic rule produced
four out of forty-two.
"""

import pytest

from src.models.transformation import TransformType
from src.services.transform_service import TransformService


@pytest.fixture
def svc():
    return TransformService.__new__(TransformService)


def run(svc, line, transform):
    """The net, given the line as both source and output."""
    return svc._apply_term_map(line, transform, source_text=line)


class TestTheOathsAustenActuallyWrote:
    """All ten, verbatim from the source."""

    @pytest.mark.parametrize(
        "line,expected",
        [
            ("But--good Lord! how unlucky!", "But--good gracious! how unlucky!"),
            ("“Lord, how tired I am!”", "“Good gracious, how tired I am!”"),
            (
                "“Good Lord! how can you tell such a story?”",
                "“Good gracious! how can you tell such a story?”",
            ),
            ("Lord! how ashamed I should be", "Good gracious! how ashamed I should be"),
            (
                "Lord! how I should like to be married",
                "Good gracious! how I should like to be married",
            ),
            ("Lord! how I laughed!", "Good gracious! how I laughed!"),
            (
                "“Oh, Lord! yes; there is nothing in that.",
                "“Good gracious! yes; there is nothing in that.",
            ),
            ("“Oh, Lord! I don’t know.", "“Good gracious! I don’t know."),
            ("Oh, Lord! what will become of me?", "Good gracious! what will become of me?"),
        ],
    )
    def test_they_become_her_own_words(self, svc, line, expected):
        assert run(svc, line, TransformType.NONBINARY) == expected

    def test_the_stacked_exclamations_survive_as_a_stack(self, svc):
        """Mrs. Bennet says four in a row, and one of them is the oath."""
        line = "“Good gracious! Lord bless me! only think! dear me!"
        assert run(svc, line, TransformType.NONBINARY) == (
            "“Good gracious! Heaven bless me! only think! dear me!"
        )


class TestThePeerIsStillAPeer:
    """Colonel Fitzwilliam's uncle is a real lord, and a title transforms."""

    @pytest.mark.parametrize(
        "transform,expected",
        [
            (TransformType.ALL_MALE, "Lord ----"),
            (TransformType.ALL_FEMALE, "Lady ----"),
            (TransformType.GENDER_SWAP, "Lady ----"),
            (TransformType.NONBINARY, "Noble ----"),
        ],
    )
    def test_the_title_transforms_rather_than_becoming_an_exclamation(
        self, svc, transform, expected
    ):
        line = "the younger son of his uncle, Lord ----; and, to the great surprise"
        assert expected in run(svc, line, transform)

    def test_a_named_lord_keeps_his_name(self, svc):
        assert "gracious" not in run(svc, "Lord Byron called.", TransformType.NONBINARY)


class TestTheVariantsThatLeaveItAlone:
    def test_all_male_has_no_anomaly_to_fix(self, svc):
        """ "Lord" is already the masculine form; nothing here is out of place."""
        line = "But--good Lord! how unlucky!"
        assert run(svc, line, TransformType.ALL_MALE) == line

    def test_but_it_is_still_never_swapped_to_a_title(self, svc):
        """Before this, the swap made the oath "Lady!"."""
        for transform in (TransformType.ALL_MALE, TransformType.GENDER_SWAP):
            out = run(svc, "Lord! how I laughed!", transform)
            assert "Lady" not in out
            assert "Noble" not in out


class TestARepairCanNowFire:
    """Each case is a real source line with the coinage the model returned."""

    @pytest.mark.parametrize(
        "source,produced,transform,expected",
        [
            # Ladyship came back six ways; all of them settle on one.
            (
                "her Ladyship was pleased",
                "their Nobship was pleased",
                TransformType.NONBINARY,
                "Nobleship",
            ),
            (
                "her Ladyship was pleased",
                "their Noblemajesty was pleased",
                TransformType.NONBINARY,
                "Nobleship",
            ),
            (
                "her Ladyship was pleased",
                "their Noblesip was pleased",
                TransformType.NONBINARY,
                "Nobleship",
            ),
            (
                "her Ladyship was pleased",
                "their Nobleperson was pleased",
                TransformType.NONBINARY,
                "Nobleship",
            ),
            # The one that already worked keeps working.
            (
                "her Ladyship was pleased",
                "her Ladyship was pleased",
                TransformType.NONBINARY,
                "Nobleship",
            ),
            # The typo rule that never could.
            ("her niece arrived", "their nibbling arrived", TransformType.NONBINARY, "nibling"),
            (
                "a clergyman of the parish",
                "a clergyperson of the parish",
                TransformType.NONBINARY,
                "cleric",
            ),
            (
                "the knighthood he received",
                "the damehood she received",
                TransformType.ALL_FEMALE,
                "knighthood",
            ),
            (
                "Oh, mamma, how could you",
                "Oh, mama, how could you",
                TransformType.GENDER_SWAP,
                "mamma",
            ),
        ],
    )
    def test_the_coinage_is_repaired(self, svc, source, produced, transform, expected):
        out = svc._apply_term_map(produced, transform, source_text=source)
        assert expected.lower() in out.lower()

    def test_a_real_word_is_not_taken_for_a_coinage(self, svc):
        """ "Nobility" means the aristocracy. It is matched only in the possessive
        frame the model used it as an honorific in, so Austen's noun is safe."""
        line = "the nobility of the county assembled"
        assert (
            "nobleship"
            not in svc._apply_term_map(line, TransformType.NONBINARY, source_text=line).lower()
        )


class TestTheMaskStillDoesItsJob:
    """The repairs are exempt from the mask; nothing else became exempt."""

    def test_correct_model_work_is_not_undone(self, svc):
        """A bidirectional map will reverse a correct rename if the mask lifts."""
        source = "Mrs. Bennet spoke to Mr. Bennet"
        produced = "Mr. Bennet spoke to Mrs. Bennet"
        assert svc._apply_term_map(produced, TransformType.GENDER_SWAP, source_text=source) == (
            produced
        )
