"""Say it once, in the plural.

A one-directional transform sends both halves of a coordinated pair to the
same word: "her uncle and aunt" becomes "his uncle and uncle". English has a
better answer, and on a real all_female run the reader chose it 22 times out
of 22 — every editorial call they made was this one shape. So it is a rule now
rather than a question.
"""

import pytest

from src.services.transform_service import TransformService as T


@pytest.fixture
def svc():
    return T.__new__(T)


def collapse(svc, text, source, key="all_female"):
    return svc._collapse_coordinated_pair(text, key, source)


# Every call the reader made, verbatim from review_decisions.json.
REAL = [
    ("their mother and mother", "their mothers"),
    ("your aunt and aunt", "your aunts"),
    ("her sister and sister", "her sisters"),
    ("her aunt and aunt", "her aunts"),
    ("my aunt and aunt", "my aunts"),
    ("our aunt and aunt", "our aunts"),
    ("your daughter and daughter", "your daughters"),
]


@pytest.mark.parametrize(("text", "expected"), REAL)
def test_it_makes_the_call_the_reader_made(svc, text, expected):
    owner, noun = text.split()[0], text.split()[1]
    assert collapse(svc, text, f"{owner} {noun} and other") == expected


class TestThePlural:
    def test_a_regular_noun(self, svc):
        assert collapse(svc, "her aunt and aunt", "her aunt and uncle") == "her aunts"

    def test_a_sibilant_takes_es(self, svc):
        """The reader typed "mistresss" by hand; the rule does better."""
        assert (
            collapse(svc, "her mistress and mistress", "her mistress and master")
            == "her mistresses"
        )

    def test_an_irregular_plural(self, svc):
        assert collapse(svc, "her wife and wife", "her wife and husband") == "her wives"

    def test_sentence_case_survives(self, svc):
        assert collapse(svc, "Her aunt and aunt", "Her aunt and uncle") == "Her aunts"


class TestWhatItLeavesAlone:
    def test_a_source_that_really_repeats(self, svc):
        """Austen wrote it twice; that is her sentence, not our collapse."""
        text = "her sister and sister"
        assert collapse(svc, text, "her sister and sister") == text

    def test_two_relations_that_stayed_different(self, svc):
        text = "her uncle and aunt"
        assert collapse(svc, text, "her uncle and aunt") == text

    def test_a_pair_with_no_possessive(self, svc):
        text = "the aunt and aunt"
        assert collapse(svc, text, "the uncle and aunt") == text

    def test_a_noun_that_is_not_a_relation(self, svc):
        text = "her book and book"
        assert collapse(svc, text, "her book and letter") == text

    def test_without_a_source_nothing_happens(self, svc):
        """No source means no way to know the two ever differed."""
        text = "her aunt and aunt"
        assert svc._collapse_coordinated_pair(text, "all_female", None) == text

    def test_a_different_possessive_on_each_half(self, svc):
        """ "her aunt and his aunt" is two people's aunts, not one pair."""
        text = "her aunt and his aunt"
        assert collapse(svc, text, "her aunt and his uncle") == text


class TestInContext:
    def test_it_works_inside_a_sentence(self, svc):
        text = "the visits of her aunt and aunt from the city were welcome"
        source = "the visits of her uncle and aunt from the city were welcome"
        assert "her aunts from the city" in collapse(svc, text, source)

    def test_two_pairs_in_one_sentence(self, svc):
        text = "her aunt and aunt met my sister and sister"
        source = "her uncle and aunt met my brother and sister"
        out = collapse(svc, text, source)
        assert "her aunts" in out and "my sisters" in out

    def test_the_rest_of_the_sentence_is_untouched(self, svc):
        text = "and though her aunt and aunt frequently invited him"
        source = "and though her uncle and aunt frequently invited him"
        assert collapse(svc, text, source) == "and though her aunts frequently invited him"


@pytest.mark.parametrize("key", ["all_female", "all_male", "gender_swap"])
def test_every_transform_gets_the_rule(svc, key):
    assert collapse(svc, "her aunt and aunt", "her uncle and aunt", key) == "her aunts"


class TestNonbinaryChangesEveryPossessive:
    """ "her" and "his" both become "their", so the possessive cannot anchor it.

    Matching on the possessive made the rule fire for "their mother and
    father" — where the source already said "their" — and never for "her uncle
    and aunt", which is the case it exists for. All 22 real decisions came from
    an all_female run, where "her" stays "her", so they all passed.
    """

    def test_a_changed_possessive_still_collapses(self, svc):
        assert (
            collapse(svc, "their relative and relative", "her uncle and aunt", "nonbinary")
            == "their relatives"
        )

    def test_an_unchanged_possessive_still_collapses(self, svc):
        assert (
            collapse(svc, "their parent and parent", "their mother and father", "nonbinary")
            == "their parents"
        )

    def test_siblings(self, svc):
        assert (
            collapse(svc, "their sibling and sibling", "her sister and brother", "nonbinary")
            == "their siblings"
        )

    def test_the_authors_own_repeat_is_still_safe(self, svc):
        """Even though the possessive changed, the source said it twice."""
        text = "their sibling and sibling"
        assert collapse(svc, text, "her sister and sister", "nonbinary") == text

    def test_pairs_are_matched_by_position(self, svc):
        """The first pair repeats in the source; the second does not."""
        out = collapse(
            svc,
            "their sibling and sibling met their relative and relative",
            "her sister and sister met her uncle and aunt",
            "nonbinary",
        )
        assert "their sibling and sibling" in out
        assert "their relatives" in out
