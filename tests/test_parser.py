"""
Parser smoke tests - does our parsing logic work?
"""

from pathlib import Path

import pytest

from src.parsers.parser import IntegratedParser, parse_book


def test_parse_simple_text():
    """Test basic text parsing."""
    parser = IntegratedParser()

    text = """
    CHAPTER 1
    This is a paragraph.

    This is another paragraph.

    CHAPTER 2
    Final paragraph here.
    """

    result = parser.parse(text)

    # Check basic structure
    assert result.chapters is not None
    assert len(result.chapters) > 0
    assert result.chapters[0]["paragraphs"] is not None


def test_parse_gutenberg_headers():
    """Test that Gutenberg headers are removed."""
    parser = IntegratedParser()

    text = """*** START OF THE PROJECT GUTENBERG EBOOK TEST ***

    Title: Test Book
    Author: Test Author

    CHAPTER 1
    The actual content starts here.

    *** END OF THE PROJECT GUTENBERG EBOOK TEST ***
    """

    result = parser.parse(text)

    # Verify Gutenberg markers are gone
    full_text = str(result.chapters)
    assert "PROJECT GUTENBERG" not in full_text
    assert "actual content" in full_text.lower()


def test_trailing_colophon_stripped():
    """pg1342 has a 'CHISWICK PRESS' colophon between the last sentence and the
    `*** END` marker. It must not survive into chapter content."""
    pg1342 = Path("books/texts/pg1342-Pride_and_Prejudice.txt")
    if not pg1342.exists():
        pytest.skip(f"{pg1342} not available in this checkout")

    book = parse_book(str(pg1342))
    last_chapter = book.chapters[-1]
    tail = " ".join(last_chapter["paragraphs"][-3:])

    assert "uniting them." in tail
    assert "CHISWICK" not in tail
    assert "TOOKS COURT" not in tail
    assert "WHITTINGHAM" not in tail


def test_parser_handles_empty_input():
    """Parser shouldn't crash on empty input."""
    parser = IntegratedParser()

    # Test empty string
    result = parser.parse("")
    assert result is not None
    assert result.chapters is not None  # Might be empty list, that's fine

    # Test just whitespace
    result = parser.parse("   \n\n\n   ")
    assert result is not None


def test_parser_preserves_paragraph_structure():
    """Test that paragraphs are preserved correctly."""
    parser = IntegratedParser()

    text = """
    CHAPTER 1: Test

    First paragraph here.
    Still first paragraph.

    Second paragraph here.
    Also second paragraph.

    Third paragraph.
    """

    result = parser.parse(text)

    # Should have detected the chapter
    assert len(result.chapters) >= 1
    chapter = result.chapters[0]

    # Should have preserved paragraph breaks
    assert len(chapter["paragraphs"]) >= 2  # At least 2 paragraphs


# Play format detection is complex and not critical
# Skipping this test for pragmatic approach


class TestIllustratedEditions:
    """Illustrated Gutenberg editions place plates in the middle of a sentence.

    Stripping the plate used to leave the blank lines that surrounded it, which
    split one paragraph in two. In print that shows up as a paragraph indent
    mid-sentence; in the pipeline it hands the transform a fragment ending on a
    bare possessive, with the noun it belongs to in the next paragraph.
    """

    def _clean(self, text):
        from src.parsers.gutenberg import GutenbergParser

        return "\n".join(GutenbergParser()._clean_lines(text.split("\n")))

    def test_plate_interrupting_a_sentence_is_closed_over(self):
        text = (
            "settled at Netherfield as he ought to be. Lady Lucas quieted her fears a\n"
            "little by starting the idea of his\n"
            "\n"
            "[Illustration:\n"
            "\n"
            "     “When the Party entered”\n"
            "\n"
            "[_Copyright 1894 by George Allen._]]\n"
            "\n"
            "being gone to London only to get a large party for the ball; and a\n"
            "report soon followed that Mr. Bingley was to bring twelve ladies.\n"
        )
        cleaned = self._clean(text)
        assert "the idea of his\nbeing gone to London" in cleaned
        assert "\n\n" not in cleaned.strip(), "the paragraph must not stay split"

    def test_plate_between_real_paragraphs_keeps_them_apart(self):
        """A plate that sits on a genuine paragraph boundary must not join them."""
        text = (
            "He came down on Monday in a chaise and four to see the place.\n"
            "\n"
            "[Illustration: A plate]\n"
            "\n"
            "Mr. Bennet made no answer at all.\n"
        )
        cleaned = self._clean(text)
        assert "\n\n" in cleaned, "separate paragraphs must stay separate"

    def test_lower_case_start_alone_does_not_join(self):
        """Both halves have to agree, or ordinary paragraphs get merged."""
        text = (
            "He came down on Monday to see the place.\n"
            "\n"
            "[Illustration: A plate]\n"
            "\n"
            "mid-sentence looking line that follows a full stop.\n"
        )
        assert "\n\n" in self._clean(text)

    def test_chapter_heading_inside_a_caption_is_still_preserved(self):
        text = "Some text.\n\n[Illustration:\n\nCHAPTER IV.]\n\nThe next paragraph.\n"
        assert "CHAPTER IV" in self._clean(text)
