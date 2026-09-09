"""A surname that is also a gendered noun must survive the term map.

Pride and Prejudice has a Mary King. The flat, case-insensitive gender_swap
map read her surname as a monarch and the printed edition calls her Mary
Queen; "Miss King" became "Miss Queen" seven times.

The cast is the only thing that knows the difference, so it is handed to the
transform before the run. Capitalised forms only, so the monarch still swaps.
"""

import pytest

from src.models.transformation import TransformType
from src.services.transform_service import TransformService


@pytest.fixture
def guarded():
    service = TransformService.__new__(TransformService)
    service.protect_names(["King", "Bennet", "Darcy", "Lucas"], TransformType.GENDER_SWAP)
    return service


@pytest.fixture
def plain():
    return TransformService.__new__(TransformService)


def swap(service, text):
    return service._apply_term_map(text, TransformType.GENDER_SWAP, text)


class TestSurnameSurvives:
    @pytest.mark.parametrize(
        "text",
        [
            "There is no danger of Wickham's marrying Mary King.",
            "Miss King is her object.",
            "she danced with Mr. King",
        ],
    )
    def test_the_surname_is_untouched(self, guarded, text):
        assert "King" in swap(guarded, text)
        assert "Queen" not in swap(guarded, text)

    def test_without_the_cast_it_is_corrupted(self, plain):
        """The behaviour this exists to stop."""
        assert "Mary Queen" in swap(plain, "Wickham is marrying Mary King.")

    def test_the_title_beside_it_still_swaps(self, guarded):
        """Only the surname is shielded, not the sentence around it."""
        assert swap(guarded, "Mr. King called on her father.") == "Mrs. King called on his mother."


class TestTheCommonNounStillSwaps:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("The king was crowned that year.", "The queen was crowned that year."),
            ("He was every inch a king.", "She was every inch a queen."),
        ],
    )
    def test_lowercase_is_not_protected(self, guarded, text, expected):
        assert swap(guarded, text) == expected


class TestWhatGetsCompiled:
    def test_only_colliding_names_are_protected(self):
        """Shielding "Darcy" would be a no-op; a short pattern stays legible."""
        service = TransformService.__new__(TransformService)
        service.protect_names(["King", "Darcy", "Bennet"], TransformType.GENDER_SWAP)
        assert "King" in service._protected_names.pattern
        assert "Darcy" not in service._protected_names.pattern

    def test_a_cast_with_no_collisions_compiles_nothing(self):
        service = TransformService.__new__(TransformService)
        service.protect_names(["Darcy", "Bennet", "Lucas"], TransformType.GENDER_SWAP)
        assert service._protected_names is None

    def test_an_unprotected_service_behaves_as_before(self, plain):
        """Every existing caller passes no cast and must be unaffected."""
        assert plain._name_spans("Mary King and the king") == []
        assert swap(plain, "Her father was a widower.") == "His mother was a widow."

    def test_it_generalises_beyond_king(self):
        service = TransformService.__new__(TransformService)
        service.protect_names(["Prince"], TransformType.GENDER_SWAP)
        assert "Prince" in swap(service, "Mr. Prince called.")
        assert "princess" in swap(service, "the prince rode out")
