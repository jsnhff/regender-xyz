"""Words in the swap map that are not always the person they name.

The nonbinary map has thirty sense rules; gender_swap had none, so it ran flat
and case-insensitive over the whole book. The printed edition says "read three
handmaids" where Austen wrote pages, and calls Sir William Lucas "Madam William
Lucas". Neither was reported, because a swapped word raises the coverage number
whether or not it was the right word to swap.
"""

import pytest

from src.models.transformation import TransformType
from src.services.transform_service import TransformService


@pytest.fixture
def swap():
    service = TransformService.__new__(TransformService)
    return lambda text: service._apply_term_map(text, TransformType.GENDER_SWAP, text)


class TestTitleBeforeAName:
    """A title before a name swaps to a title, not to a form of address.

    "Sir" has two answers in a swap: "madam" when it is an address, "Lady" when
    it sits on a name. The flat map only knew the first, so the printed edition
    calls Sir William Lucas "Madam William Lucas" -- a form that does not exist
    in English.
    """

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("by Sir William Lucas's information", "by Lady William Lucas's information"),
            ("Sir Lewis de Bourgh had been knighted", "Lady Lewis de Bourgh had been knighted"),
        ],
    )
    def test_sir_before_a_name_becomes_lady(self, swap, text, expected):
        assert swap(text) == expected

    def test_it_never_becomes_madam(self, swap):
        assert "Madam" not in swap("by Sir William Lucas's accidental information")

    def test_lady_and_lord_still_swap_normally(self, swap):
        """They are already titles that sit on a name; only Sir was broken."""
        assert swap("Lady Catherine was indignant") == "Lord Catherine was indignant"

    def test_a_bare_vocative_still_swaps(self, swap):
        """ "Yes, sir" is an address, not a title on a name."""
        assert swap("Yes, sir, I know I am.") == "Yes, madam, I know I am."

    def test_a_bare_madam_still_swaps(self, swap):
        assert swap("Yes, madam, I know I am.") == "Yes, sir, I know I am."


class TestPage:
    """All three uses in Austen are the reading kind."""

    @pytest.mark.parametrize(
        "text",
        [
            "before she had read three pages",
            "scarcely knowing anything of the last page or two",
            "looking at her page",
        ],
    )
    def test_a_page_is_not_a_servant(self, swap, text):
        assert "handmaid" not in swap(text)


class TestOtherPolysemousWords:
    @pytest.mark.parametrize(
        "text,forbidden",
        [
            ("I count on your discretion.", "countess"),
            ("She counts upon his coming.", "countess"),
            ("a host of friends", "hostess"),
            ("She took up a rake.", "harlot"),
            ("the rake leaned against the wall", "harlot"),
        ],
    )
    def test_the_common_sense_is_left_alone(self, swap, text, forbidden):
        assert forbidden not in swap(text).lower()


class TestTheSwapStillWorks:
    """The guard must not blunt the transform it is protecting."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("Her father was a widower.", "His mother was a widow."),
            ("He was every inch a king.", "She was every inch a queen."),
            ("the master of the house", "the mistress of the house"),
            ("his son and her daughter", "her daughter and his son"),
        ],
    )
    def test_ordinary_swaps_are_untouched(self, swap, text, expected):
        assert swap(text) == expected

    def test_other_transforms_have_no_frames(self):
        """Only gender_swap carries these; nonbinary has its own sense rules."""
        assert TransformService.protected_spans("Sir William Lucas", "nonbinary") == []
        assert TransformService.protected_spans("Sir William Lucas", "gender_swap") != []

    def test_the_default_call_still_works(self):
        """qc_service calls this with no key."""
        assert TransformService.protected_spans("Good Lord, what a thing") != []
