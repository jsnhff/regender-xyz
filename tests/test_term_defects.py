"""Four defects in the deterministic net, each with shipped damage.

Everything here was measured in the four shipped editions against the source,
so each test names a real sentence that reached a printed page.
"""

import pytest

from src.models.transformation import TransformType
from src.services.transform_service import TransformService


@pytest.fixture
def svc():
    return TransformService.__new__(TransformService)


class TestTheTableThatWasDefinedTwice:
    """A second, shorter copy of _IRREGULAR_PLURALS sat further down the class
    body, and being later it silently won -- dropping gentleman, gentlewoman,
    kinsman, kinswoman and hero from every lookup.

    So "gentlemen" was never in a term map at all. The gender-swap edition holds
    74 of them, unswapped, against 40 in the source: the count went up because
    nothing touched the word and the model added some of its own.
    """

    @pytest.mark.parametrize(
        "word,plural",
        [
            ("gentleman", "gentlemen"),
            ("gentlewoman", "gentlewomen"),
            ("kinsman", "kinsmen"),
            ("kinswoman", "kinswomen"),
            ("hero", "heroes"),
            ("man", "men"),
            ("woman", "women"),
            ("child", "children"),
            ("person", "people"),
            ("wife", "wives"),
        ],
    )
    def test_the_irregular_plurals_are_all_present(self, word, plural):
        assert TransformService._pluralize(word) == plural

    def test_there_is_only_one_definition(self):
        import inspect

        source = inspect.getsource(TransformService)
        assert source.count("_IRREGULAR_PLURALS: dict[str, str] = {") == 1
        assert source.count("_IRREGULAR_PLURALS = {") == 0

    def test_gentlemen_actually_swaps_now(self, svc):
        line = "The two gentlemen left Rosings."
        assert svc._apply_term_map(line, TransformType.GENDER_SWAP) == (
            "The two gentlewomen left Rosings."
        )

    def test_and_heroines_do_not_become_heros(self, svc):
        assert svc._apply_term_map("The heroines of the tale.", TransformType.ALL_MALE) == (
            "The heroes of the tale."
        )


class TestPluralisingAWordThatIsAlreadyPlural:
    """A coordinated pair is collapsed by pluralising the word both halves map
    to, and for nonbinary "uncle and aunt" both map to "relatives" -- plural
    already. Pluralising again put "Who are your relativeses?" into Lady
    Catherine's interrogation of Elizabeth, in the shipped edition.
    """

    @pytest.mark.parametrize(
        "noun,expected",
        [
            ("relatives", "relatives"),
            ("siblings", "siblings"),
            ("children", "children"),
            ("people", "people"),
            # And a singular must still be pluralised.
            ("relative", "relatives"),
            ("uncle", "uncles"),
            ("child", "children"),
            ("wife", "wives"),
        ],
    )
    def test_it_is_left_alone(self, noun, expected):
        assert TransformService._plural_of(noun) == expected

    def test_the_shipped_sentence(self, svc):
        line = "Who are your uncles and aunts?"
        assert svc._apply_term_map(line, TransformType.NONBINARY, source_text=line) == (
            "Who are your relatives?"
        )


class TestTheSenseOfAWordIsNotItsGender:
    """Sense rules were defined for the nonbinary variant only, so the others
    swapped "master" blind. Austen's two uses of the plural both mean teachers
    -- "for the benefit of masters" -- and the gender-swap and all-female
    editions read "for the benefit of mistresses", which says something else.
    """

    @pytest.mark.parametrize(
        "transform",
        [
            TransformType.GENDER_SWAP,
            TransformType.ALL_MALE,
            TransformType.ALL_FEMALE,
            TransformType.NONBINARY,
        ],
    )
    def test_masters_who_teach_become_teachers_in_every_variant(self, svc, transform):
        line = "for the benefit of masters."
        assert svc._apply_term_map(line, transform, source_text=line) == (
            "for the benefit of teachers."
        )

    @pytest.mark.parametrize(
        "transform", [TransformType.GENDER_SWAP, TransformType.ALL_FEMALE, TransformType.ALL_MALE]
    )
    def test_the_named_teaching_frames_too(self, svc, transform):
        line = "a music master in London."
        assert "music teacher" in svc._apply_term_map(line, transform, source_text=line)

    def test_but_the_idioms_are_not_flattened(self, svc):
        """ "her own mistress" really does become "his own master", and the
        household sense really does cross over. Sharing those would have cost
        the book two correct idioms to fix one wrong sense."""
        line = "she was her own mistress."
        out = svc._apply_term_map(line, TransformType.ALL_MALE, source_text=line)
        assert "own person" not in out


class TestOneHonorificPerEdition:
    """The all-female net wrote "Ms." while the name map wrote "Mrs." -- 202
    against 551 in the shipped edition, the same honorific two ways at close to
    half and half, and "Ms." did not exist in 1813.
    """

    def test_the_net_agrees_with_the_map(self):
        assert TransformService._effective_term_map("all_female")["Mr"] == "Mrs"

    def test_no_anachronism_reaches_the_page(self, svc):
        line = "Mr. Stone was announced."
        assert svc._apply_term_map(line, TransformType.ALL_FEMALE, source_text=line) == (
            "Mrs. Stone was announced."
        )
