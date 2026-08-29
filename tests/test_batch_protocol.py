"""Tests for the batch request/response protocol.

A batch response has to be mapped back onto its source paragraphs exactly. The
previous parser split on blank lines and, on any mismatch, padded with empty
strings or truncated — silently deleting paragraphs from the book, or shifting
every later paragraph in the chapter into the wrong slot.
"""

import logging

import pytest

from src.exceptions import BatchResponseError
from src.models.book import Paragraph
from src.models.transformation import TransformType
from src.services.transform_service import TransformService


@pytest.fixture(scope="module")
def service():
    """A bare service: the batch protocol needs no provider, only a logger."""
    instance = TransformService.__new__(TransformService)
    instance.logger = logging.getLogger("test.transform")
    return instance


class TestPromptCarriesMarkers:
    def test_each_paragraph_is_marked(self, service):
        paragraphs = [Paragraph(sentences=[f"Paragraph {i}."]) for i in range(1, 4)]
        prompt = service._create_batch_transform_prompt(
            paragraphs, {"transform_type": TransformType.GENDER_SWAP}, 3
        )
        for index in (1, 2, 3):
            assert f"[[P{index}]]" in prompt["user"]
        assert "unchanged marker" in prompt["system"]


class TestMarkedResponses:
    def test_markers_are_mapped_in_order(self, service):
        response = "[[P1]]\nFirst.\n\n[[P2]]\nSecond.\n\n[[P3]]\nThird."
        assert service._parse_batch_response(response, 3) == ["First.", "Second.", "Third."]

    def test_markers_survive_a_preamble(self, service):
        """A chatty model used to shift every paragraph by one."""
        response = "Here are the transformed paragraphs:\n\n[[P1]]\nFirst.\n\n[[P2]]\nSecond."
        assert service._parse_batch_response(response, 2) == ["First.", "Second."]

    def test_markers_survive_a_blank_line_inside_a_paragraph(self, service):
        """Verse and letters carry their own blank lines."""
        response = "[[P1]]\nA line.\n\nStill the same paragraph.\n\n[[P2]]\nSecond."
        first, second = service._parse_batch_response(response, 2)
        assert "Still the same paragraph." in first
        assert second == "Second."

    def test_out_of_order_markers_are_restored_to_source_order(self, service):
        response = "[[P2]]\nSecond.\n\n[[P1]]\nFirst."
        assert service._parse_batch_response(response, 2) == ["First.", "Second."]


class TestUnmappableResponses:
    def test_missing_paragraph_raises_instead_of_padding(self, service):
        """Padding with empty strings deleted paragraphs from the book."""
        with pytest.raises(BatchResponseError):
            service._parse_batch_response("Only one paragraph came back.", 3)

    def test_extra_paragraph_raises_instead_of_truncating(self, service):
        with pytest.raises(BatchResponseError):
            service._parse_batch_response("One.\n\nTwo.\n\nThree.\n\nFour.", 3)

    def test_partial_markers_raise(self, service):
        with pytest.raises(BatchResponseError):
            service._parse_batch_response("[[P1]]\nFirst.\n\nSecond without a marker.", 3)

    def test_error_names_what_it_saw(self, service):
        with pytest.raises(BatchResponseError, match="Expected 3 paragraphs"):
            service._parse_batch_response("One.", 3)


class TestBackwardCompatibility:
    def test_unmarked_response_with_the_right_count_still_works(self, service):
        """Older models that ignore the markers are still handled."""
        assert service._parse_batch_response("One.\n\nTwo.", 2) == ["One.", "Two."]

    def test_a_single_paragraph_is_never_ambiguous(self, service):
        response = "A paragraph that\n\nhappens to contain a blank line."
        assert service._parse_batch_response(response, 1) == [response]

    def test_a_single_paragraph_has_its_marker_stripped(self, service):
        assert service._parse_batch_response("[[P1]]\nJust this.", 1) == ["Just this."]
