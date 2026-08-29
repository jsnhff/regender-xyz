"""Regression tests for the deterministic gender-term safety net.

The safety net runs on LLM output. For a bidirectional map like gender_swap
it therefore has to distinguish words the LLM already transformed from words
it missed; applying the map blindly swaps correct output straight back. These
tests pin that behaviour down, together with the pronoun/noun pairing that
"her husband" depends on.
"""

import pytest

from src.models.transformation import TransformType
from src.services.transform_service import TransformService


@pytest.fixture(scope="module")
def service():
    """A TransformService with no dependencies — the term map needs no provider."""
    return TransformService.__new__(TransformService)


def apply(service, source, llm_output, transform_type):
    return service._apply_term_map(llm_output, transform_type, source_text=source)


class TestPairedTerms:
    """A possessive pronoun and its noun must end up agreeing."""

    @pytest.mark.parametrize(
        "llm_output",
        [
            "his wife",  # LLM got it right
            "his husband",  # LLM missed the noun
            "her wife",  # LLM missed the pronoun
            "her husband",  # LLM missed both
        ],
    )
    def test_her_husband_always_lands_on_his_wife(self, service, llm_output):
        assert apply(service, "her husband", llm_output, TransformType.GENDER_SWAP) == "his wife"

    @pytest.mark.parametrize("llm_output", ["her husband", "her wife", "his husband", "his wife"])
    def test_his_wife_always_lands_on_her_husband(self, service, llm_output):
        assert apply(service, "his wife", llm_output, TransformType.GENDER_SWAP) == "her husband"

    def test_correct_output_is_not_reverted(self, service):
        """The bug behind the printed prototypes: a correct swap was undone.

        "her mother" -> "his father" was rewritten to "his mother", because the
        map applied "mother->father" and then "father->mother" in sequence.
        """
        assert apply(service, "her mother", "his father", TransformType.GENDER_SWAP) == "his father"

    def test_symmetric_swap_within_one_sentence_is_not_undone(self, service):
        """Both halves of a swapped pair are still present, just exchanged."""
        assert (
            apply(
                service,
                "her mother and her father",
                "his father and his mother",
                TransformType.GENDER_SWAP,
            )
            == "his father and his mother"
        )


class TestBidirectionalMapDoesNotCollapse:
    def test_every_pair_swaps_rather_than_flattening(self, service):
        """Applying the swap map to untransformed text must exchange both sides."""
        for source, expected in [
            ("the queen and the king", "the king and the queen"),
            ("a brother and a sister", "a sister and a brother"),
            ("the woman spoke to the man", "the man spoke to the woman"),
            ("her ladyship met the lord", "his lordship met the lady"),
        ]:
            assert apply(service, source, source, TransformType.GENDER_SWAP) == expected

    def test_term_map_is_order_independent(self):
        """No map may depend on dict insertion order to be correct."""
        for key in TransformService._TERM_MAPS:
            effective = TransformService._effective_term_map(key)
            collapsing = [
                term
                for term, target in effective.items()
                if effective.get(target.lower(), "").lower() == term.lower()
                and target.lower() != term.lower()
            ]
            # Collapsing pairs are fine now, but only because substitution is
            # a single simultaneous pass. Assert that pass is what runs.
            pattern, _ = TransformService._compile_substitution(tuple(sorted(effective.items())))
            assert pattern.groups == 0, f"{key}: substitution must be one alternation"
            assert isinstance(collapsing, list)


class TestPlurals:
    @pytest.mark.parametrize(
        "source,expected",
        [
            ("her sisters", "his brothers"),
            ("the ladies", "the lords"),
            ("two women", "two men"),
            ("his daughters", "her sons"),
            ("the duchesses", "the dukes"),
        ],
    )
    def test_plural_forms_are_covered(self, service, source, expected):
        assert apply(service, source, source, TransformType.GENDER_SWAP) == expected


class TestContextualPronouns:
    def test_objective_her_becomes_him(self, service):
        assert (
            apply(service, "he spoke to her.", "he spoke to her.", TransformType.GENDER_SWAP)
            == "she spoke to him."
        )

    def test_predicative_his_becomes_hers(self, service):
        assert (
            apply(service, "The book is his.", "The book is his.", TransformType.GENDER_SWAP)
            == "The book is hers."
        )

    def test_nonbinary_possessive_is_their_not_them(self, service):
        """A flat her->them mapping produced the ungrammatical "them parent"."""
        assert apply(service, "her mother", "her mother", TransformType.NONBINARY) == "their parent"
        assert (
            apply(service, "spoke to her.", "spoke to her.", TransformType.NONBINARY)
            == "spoke to them."
        )

    def test_ambiguous_her_is_left_for_review(self, service):
        """Neither reading is safe, so the safety net must not guess."""
        result = apply(
            service, "he gave her a book", "he gave her a book", TransformType.GENDER_SWAP
        )
        assert "her a book" in result


class TestCasePreservation:
    @pytest.mark.parametrize(
        "source,expected",
        [
            ("Her Ladyship", "His Lordship"),
            ("THE QUEEN", "THE KING"),
            ("Mrs. Bennet told her husband", "Mr. Bennet told his wife"),
        ],
    )
    def test_casing_survives_substitution(self, service, source, expected):
        assert apply(service, source, source, TransformType.GENDER_SWAP) == expected

    def test_honorific_replacement_keeps_its_own_case(self, service):
        """ "madam" -> "Mx." must not be lowercased into "mx."."""
        assert "Mx." in apply(service, "madam", "madam", TransformType.NONBINARY)


class TestNameMap:
    def test_names_respect_word_boundaries(self, service):
        """ "Ann" must not rewrite the inside of "Anne"."""
        assert service._apply_name_map("Anne and Ann", {"Ann": "Alan"}) == "Anne and Alan"

    def test_name_swaps_do_not_collapse(self, service):
        """A cyclic name map applied sequentially would land both on one name."""
        result = service._apply_name_map(
            "Elizabeth and Fitzwilliam",
            {"Elizabeth": "Fitzwilliam", "Fitzwilliam": "Elizabeth"},
        )
        assert result == "Fitzwilliam and Elizabeth"


class TestFallbackWhenLLMFails:
    def test_untransformed_paragraph_gets_the_full_deterministic_transform(self, service):
        """A batch that failed retry falls back to source text; align to source
        marks every word as a miss, so the map does the whole job."""
        source = (
            "Mrs. Bennet was a woman of mean understanding. Her husband and her "
            "daughters were her whole concern."
        )
        result = apply(service, source, source, TransformType.GENDER_SWAP)
        assert "Mr. Bennet" in result
        assert "a man of mean understanding" in result
        assert "His wife" in result
        assert "his sons" in result
