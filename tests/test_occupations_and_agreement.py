"""The words that carry gender in the word itself, and the verb after them.

No variant had a rule for -man occupationals, so the model invented an answer
each time and the four editions between them produced nine different coined
forms: gentleperson, clergyperson, chamberperson, horseperson, tradesperson,
spokesperson, sportspeople, footwoman, sportswomen. "clergyman" alone came back
as three spellings inside one edition.

Four words the audit reported as untransformed everywhere are deliberately left
alone: "lover", "rector", "milliner" and "knighthood" carry no gender in English.
That is why "damehood" is a repair rather than a rule -- a woman receives a
knighthood too.

And agreement needed a second look, because the first pass is what creates the
disagreement. The substitution is one simultaneous scan, so where "she" became
"they" the scanner had already moved on and "they was" was never a candidate:
the rule fired when handed "they was very glad" and never on "she was very
glad", which is the only way it arrives.
"""

import pytest

from src.models.transformation import TransformType
from src.services.transform_service import TransformService


@pytest.fixture
def svc():
    return TransformService.__new__(TransformService)


def run(svc, line, transform):
    return svc._apply_term_map(line, transform, source_text=line)


class TestOccupationsThatCarryGender:
    @pytest.mark.parametrize(
        "word,all_male,all_female,nonbinary",
        [
            ("clergyman", "clergyman", "clergywoman", "cleric"),
            ("coachman", "coachman", "coachwoman", "driver"),
            ("tradesman", "tradesman", "tradeswoman", "trader"),
            ("footman", "footman", "footwoman", "attendant"),
            ("spokesman", "spokesman", "spokeswoman", "speaker"),
            ("horsewoman", "horseman", "horsewoman", "rider"),
            ("patroness", "patron", "patroness", "patron"),
        ],
    )
    def test_each_variant_has_an_answer(self, svc, word, all_male, all_female, nonbinary):
        for transform, expected in (
            (TransformType.ALL_MALE, all_male),
            (TransformType.ALL_FEMALE, all_female),
            (TransformType.NONBINARY, nonbinary),
        ):
            assert expected in run(svc, f"the {word} arrived", transform), (
                f"{word} in {transform.value}"
            )

    def test_the_plural_the_source_actually_uses(self, svc):
        """ "sportsmen" is the form in the book; derived regularly from
        "sportsman" it comes out "sportsmans" and matches nothing."""
        assert "sportswomen" in run(svc, "the sportsmen gathered", TransformType.ALL_FEMALE)

    @pytest.mark.parametrize(
        "word",
        ["clergyman", "coachman", "tradesman", "footman", "spokesman", "sportsman", "horseman"],
    )
    def test_every_occupational_has_its_irregular_plural(self, word):
        assert TransformService._pluralize(word) == word[:-3] + "men"

    def test_gentlemen_keep_their_station(self, svc):
        """ "the two people" loses what Austen means by the word; "gentlefolk"
        is the period word that keeps it."""
        assert run(svc, "The two gentlemen left Rosings.", TransformType.NONBINARY) == (
            "The two gentlefolk left Rosings."
        )


class TestWordsThatCarryNoGender:
    @pytest.mark.parametrize("word", ["lover", "lovers", "rector", "milliner", "knighthood"])
    @pytest.mark.parametrize(
        "transform",
        [
            TransformType.ALL_MALE,
            TransformType.ALL_FEMALE,
            TransformType.GENDER_SWAP,
            TransformType.NONBINARY,
        ],
    )
    def test_they_are_left_alone(self, svc, word, transform):
        line = f"the {word} was there"
        assert word in run(svc, line, transform)


class TestAgreementAfterThePronounChanges:
    @pytest.mark.parametrize(
        "line,expected",
        [
            ("she was there", "they were there"),
            ("he has gone", "they have gone"),
            ("she wasn't ready", "they weren't ready"),
            ("he does not know", "they do not know"),
            ("she is happy", "they are happy"),
        ],
    )
    def test_the_verb_follows(self, svc, line, expected):
        assert run(svc, line, TransformType.NONBINARY) == expected

    def test_it_still_works_when_handed_the_phrase_directly(self, svc):
        assert run(svc, "they was very glad", TransformType.NONBINARY) == "they were very glad"

    def test_a_swap_is_not_disturbed_by_the_second_pass(self, svc):
        """The second pass is grammar, so it is exempt from the residual mask --
        which means it must not touch anything else."""
        source = "Mrs. Bennet spoke to Mr. Bennet"
        produced = "Mr. Bennet spoke to Mrs. Bennet"
        assert (
            svc._apply_term_map(produced, TransformType.GENDER_SWAP, source_text=source) == produced
        )
