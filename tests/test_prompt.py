"""Tests for the prompt the pipeline actually sends.

The prompt was only ever inspected as a template. Rendered, it turned out to
interpolate the rules as a raw Python dict repr, to tell a gender_swap to
collapse the very pairs it exists to exchange, and to hand every transform the
same possessive rule. None of that is visible without rendering it.
"""

import pytest

from src.models.book import Paragraph
from src.models.transformation import TransformType
from src.services.transform_service import TransformService


@pytest.fixture(scope="module")
def service():
    return TransformService.__new__(TransformService)


def system_prompt(service, transform_type, batch_size=3):
    context = {
        "transform_type": transform_type,
        "rules": service._get_transformation_rules(transform_type),
    }
    paragraphs = [Paragraph(sentences=["x"]) for _ in range(batch_size)]
    return service._create_batch_transform_prompt(paragraphs, context, batch_size)["system"]


class TestTaskIsStatedPlainly:
    @pytest.mark.parametrize(
        "transform_type,expected",
        [
            (TransformType.GENDER_SWAP, "Swap the gender of every character"),
            (TransformType.ALL_MALE, "Make every character male"),
            (TransformType.ALL_FEMALE, "Make every character female"),
            (TransformType.NONBINARY, "Make every character non-binary"),
        ],
    )
    def test_each_transform_says_what_it_wants(self, service, transform_type, expected):
        assert expected in system_prompt(service, transform_type)

    def test_rules_are_not_a_python_repr(self, service):
        """The task used to arrive as "{'swap': True, 'pronouns': {...}}"."""
        rendered = system_prompt(service, TransformType.GENDER_SWAP)
        assert "{'" not in rendered and "':" not in rendered

    def test_rules_are_offered_as_examples_not_a_closed_list(self, service):
        assert "not an exhaustive list" in system_prompt(service, TransformType.GENDER_SWAP)


class TestPairedTerms:
    def test_swap_is_told_to_exchange_pairs(self, service):
        """Collapsing "ladies and gentlemen" onto one gender is right for a
        single-target transform and destructive for a swap, which has none."""
        rendered = system_prompt(service, TransformType.GENDER_SWAP)
        assert "Never collapse a pair onto one gender" in rendered
        assert "simplify to the target gender" not in rendered

    @pytest.mark.parametrize("transform_type", [TransformType.ALL_MALE, TransformType.ALL_FEMALE])
    def test_single_target_transforms_still_collapse_pairs(self, service, transform_type):
        assert "simplify to the target gender" in system_prompt(service, transform_type)


class TestPossessives:
    def test_swap_moves_both_pronouns(self, service):
        rendered = system_prompt(service, TransformType.GENDER_SWAP)
        assert '"his" before a noun becomes "her"' in rendered
        assert '"her" before a noun becomes "his"' in rendered

    def test_all_female_leaves_her_alone(self, service):
        """ "her" is already on target; telling the model to move it is wrong."""
        rendered = system_prompt(service, TransformType.ALL_FEMALE)
        assert '"her" and "hers" are already correct' in rendered
        assert '"her" before a noun becomes "his"' not in rendered

    def test_all_male_leaves_his_alone(self, service):
        rendered = system_prompt(service, TransformType.ALL_MALE)
        assert '"his" is already correct' in rendered

    def test_predicative_form_is_distinguished(self, service):
        """ "his" -> "hers" for every occurrence produces "hers name"."""
        rendered = system_prompt(service, TransformType.GENDER_SWAP)
        assert "the book is hers" in rendered


class TestProtocol:
    def test_marker_contract_is_stated(self, service):
        rendered = system_prompt(service, TransformType.GENDER_SWAP)
        assert "[[Pn]]" in rendered
        assert "Do not merge, split, drop or reorder" in rendered

    def test_batch_size_agrees_with_the_paragraphs_sent(self, service):
        context = {
            "transform_type": TransformType.GENDER_SWAP,
            "rules": service._get_transformation_rules(TransformType.GENDER_SWAP),
        }
        paragraphs = [Paragraph(sentences=[f"P{i}"]) for i in range(4)]
        prompt = service._create_batch_transform_prompt(paragraphs, context, 4)
        assert "Return EXACTLY 4 paragraphs" in prompt["system"]
        assert prompt["user"].count("[[P") == 4

    def test_singular_batch_reads_correctly(self, service):
        assert "Transform 1 paragraph." in system_prompt(
            service, TransformType.GENDER_SWAP, batch_size=1
        )
