"""How many characters a run actually regenders.

A finished run reported the size of the cast it analysed, which is a fact
about the book rather than about the transformation. This is the number that
says what happened, so it has to agree with what the rename engine did.
"""

import pytest

from src.app import _cast_summary
from src.models.character import Character, Gender
from src.models.transformation import TransformType
from src.services.name_engine import NameEngine, target_gender


def cast(*genders):
    return [Character(name=f"C{i}", gender=g, pronouns={}) for i, g in enumerate(genders)]


PANDP = cast(*([Gender.MALE] * 34 + [Gender.FEMALE] * 49 + [Gender.UNKNOWN] * 7))


class TestWhoChanges:
    def test_a_swap_regenders_every_gendered_character(self):
        summary = _cast_summary(PANDP, TransformType.GENDER_SWAP)
        assert summary["regendered"] == 83
        assert summary["total"] == 90

    def test_all_female_touches_only_the_men(self):
        assert _cast_summary(PANDP, TransformType.ALL_FEMALE)["regendered"] == 34

    def test_all_male_touches_only_the_women(self):
        assert _cast_summary(PANDP, TransformType.ALL_MALE)["regendered"] == 49

    def test_a_character_of_unknown_gender_is_left_alone(self):
        """Seven of P&P's ninety have no gender to change."""
        for transform in TransformType:
            summary = _cast_summary(PANDP, transform)
            assert summary["regendered"] <= 83


class TestTheDirection:
    def test_a_swap_reports_both_ways(self):
        changes = _cast_summary(PANDP, TransformType.GENDER_SWAP)["changes"]
        assert {(c["from"], c["to"]): c["count"] for c in changes} == {
            ("male", "female"): 34,
            ("female", "male"): 49,
        }

    def test_nonbinary_reports_one_destination(self):
        changes = _cast_summary(PANDP, TransformType.NONBINARY)["changes"]
        assert {c["to"] for c in changes} == {"non-binary"}

    def test_the_largest_group_is_listed_first(self):
        changes = _cast_summary(PANDP, TransformType.GENDER_SWAP)["changes"]
        assert [c["count"] for c in changes] == sorted((c["count"] for c in changes), reverse=True)

    def test_the_counts_add_up_to_the_total_regendered(self):
        summary = _cast_summary(PANDP, TransformType.GENDER_SWAP)
        assert sum(c["count"] for c in summary["changes"]) == summary["regendered"]


class TestItAgreesWithTheEngine:
    """The summary must count exactly the characters the transform acts on."""

    @pytest.mark.parametrize("transform", list(TransformType))
    def test_the_count_matches_what_the_rename_engine_selects(self, transform):
        engine = NameEngine.__new__(NameEngine)
        selected = sum(1 for c in PANDP if engine._needs_rename(c, transform, None))
        assert _cast_summary(PANDP, transform)["regendered"] == selected

    @pytest.mark.parametrize("transform", list(TransformType))
    def test_a_character_changes_exactly_when_they_have_a_target(self, transform):
        engine = NameEngine.__new__(NameEngine)
        for char in cast(Gender.MALE, Gender.FEMALE, Gender.UNKNOWN, Gender.NONBINARY):
            has_target = target_gender(char.gender, transform) is not None
            assert has_target == engine._needs_rename(char, transform, None)


class TestEdges:
    def test_an_empty_cast_does_not_divide_by_anything(self):
        assert _cast_summary([], TransformType.GENDER_SWAP) == {
            "total": 0,
            "regendered": 0,
            "changes": [],
        }

    def test_a_cast_with_no_gendered_characters_reports_none_changed(self):
        summary = _cast_summary(cast(Gender.UNKNOWN, Gender.NEUTRAL), TransformType.GENDER_SWAP)
        assert summary == {"total": 2, "regendered": 0, "changes": []}

    def test_a_target_is_never_the_gender_it_started_as(self):
        for transform in TransformType:
            for gender in (Gender.MALE, Gender.FEMALE):
                assert target_gender(gender, transform) != gender
