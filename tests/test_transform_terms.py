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
            # One alternation, one pass. The only capturing groups are the two
            # structural ones (the term and an optional possessive clitic); a
            # per-term group would mean the map had been split into passes.
            assert set(pattern.groupindex) == {
                "term",
                "clitic",
            }, f"{key}: substitution must be one alternation"
            assert pattern.groups == 2, f"{key}: substitution must be one alternation"
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

    def test_objective_her_before_a_determiner(self, service):
        """ "gave her a book" cannot be possessive — nothing follows "her a"."""
        assert (
            apply(
                service,
                "he gave her a book",
                "he gave her a book",
                TransformType.GENDER_SWAP,
            )
            == "she gave him a book"
        )

    def test_possessive_his_before_an_ordinary_noun(self, service):
        """ "his" has no objective form, so a following content word is possessed."""
        assert (
            apply(service, "What is his name?", "What is his name?", TransformType.GENDER_SWAP)
            == "What is her name?"
        )

    def test_standalone_his_before_a_preposition(self, service):
        assert (
            apply(
                service,
                "a friend of his in town",
                "a friend of his in town",
                TransformType.GENDER_SWAP,
            )
            == "a friend of hers in town"
        )

    def test_adverb_marks_her_as_objective(self, service):
        """A possessive determiner is never followed by an adverb."""
        assert (
            apply(
                service,
                "he danced with her twice",
                "he danced with her twice",
                TransformType.GENDER_SWAP,
            )
            == "she danced with him twice"
        )

    @pytest.mark.parametrize(
        "source,expected",
        [
            ("her housekeeping", "his housekeeping"),
            ("catching her eye", "catching his eye"),
            ("the business of her life", "the business of his life"),
        ],
    )
    def test_content_word_marks_her_as_possessive(self, service, source, expected):
        assert apply(service, source, source, TransformType.GENDER_SWAP) == expected

    def test_object_complement_is_a_known_limitation(self, service):
        """Objective "her" before a participle is not distinguishable from the
        possessive gerund in "depend on her serving you" without parsing. The
        rule takes the possessive reading, which the Pride and Prejudice text
        shows is by far the common one. Pinned here so the trade-off stays
        visible rather than being discovered in print.
        """
        assert (
            apply(service, "he saw her walking", "he saw her walking", TransformType.GENDER_SWAP)
            == "she saw his walking"
        )


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


class TestPossessives:
    """A gendered noun in the possessive is still a gendered noun.

    The safety net used to skip every one of them: the boundary after a term
    refused a following apostrophe, and the source text's curly apostrophe
    against the LLM's straight one meant the two never compared equal, so a
    miss was read as a success. Roughly 79 kinship possessives survived
    untransformed in the printed Pride and Prejudice.
    """

    @pytest.mark.parametrize(
        "source,llm_output,expected",
        [
            ("her sister\u2019s room", "his sister's room", "his brother's room"),
            ("my mother\u2019s purpose", "my mother's purpose", "my father's purpose"),
            ("their aunt\u2019s house", "their aunt's house", "their uncle's house"),
            ("her daughter\u2019s proposal", "his daughter's proposal", "his son's proposal"),
            ("his father\u2019s estate", "her father's estate", "her mother's estate"),
        ],
    )
    def test_possessive_kinship_terms_are_transformed(self, service, source, llm_output, expected):
        assert (
            service._apply_term_map(llm_output, TransformType.GENDER_SWAP, source_text=source)
            == expected
        )

    def test_correct_possessive_is_not_swapped_back(self, service):
        """The net must not undo a possessive the LLM already got right."""
        assert (
            service._apply_term_map(
                "his mother's estate",
                TransformType.GENDER_SWAP,
                source_text="her father\u2019s estate",
            )
            == "his mother's estate"
        )


class TestProtectedPhrases:
    """ "Good Lord!" is an exclamation, not a character.

    The printed Pride and Prejudice carries "Good Lady!" twice and "Lady bless
    me!" once, because the term map saw only a gendered title.
    """

    @pytest.mark.parametrize(
        "source,llm_output",
        [
            ("But--good Lord! how unlucky!", "But--good Lord! how unlucky!"),
            ("Good Lord! Sir William, how can you", "Good Lord! Lady William, how can you"),
            ("Lord bless me! only think!", "Lord bless me! only think!"),
        ],
    )
    def test_exclamations_are_not_swapped(self, service, source, llm_output):
        assert (
            service._apply_term_map(llm_output, TransformType.GENDER_SWAP, source_text=source)
            == llm_output
        )

    def test_a_real_title_still_swaps(self, service):
        """The guard must not shield an actual Lady."""
        assert (
            service._apply_term_map(
                "Lady Catherine was indignant",
                TransformType.GENDER_SWAP,
                source_text="Lady Catherine was indignant",
            )
            == "Lord Catherine was indignant"
        )


class TestSenseRules:
    """Words whose sense has to be read off the words beside them.

    "master" is an employer, a teacher, a household head, a proprietor, and
    half of the "his own master" idiom. A blanket mapping to "owner" produced
    "they are their own owner" and "a London owner" in the nonbinary book.
    """

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("they are their own master", "they are their own person"),
            ("a London music master", "a London music teacher"),
            ("I asked my master", "I asked my employer"),
            ("your master is absent", "your employer is absent"),
            ("Netherfield and its master", "Netherfield and its owner"),
            ("made them master of this fortune", "made them owner of this fortune"),
            ("mistress of the house", "head of the house"),
        ],
    )
    def test_sense_is_read_from_the_collocation(self, service, text, expected):
        assert service._apply_term_map(text, TransformType.NONBINARY, source_text=text) == expected

    def test_a_sense_rule_applies_even_when_the_model_already_moved_the_word(self):
        """The source said "mistress"; the model wrote "master". Still wrong."""
        assert (
            service_nb()._apply_term_map(
                "they are their own master",
                TransformType.NONBINARY,
                source_text="she is her own mistress",
            )
            == "they are their own person"
        )

    def test_verb_agreement_applies_against_a_source(self):
        """The 100 agreement entries were dead: "they" never matches "she"."""
        assert (
            service_nb()._apply_term_map(
                "They was glad.", TransformType.NONBINARY, source_text="She was glad."
            )
            == "They were glad."
        )


def service_nb():
    return TransformService.__new__(TransformService)
