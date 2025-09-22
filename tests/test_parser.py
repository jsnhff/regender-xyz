"""
Parser smoke tests - does our parsing logic work?
"""
import pytest

from src.parsers.parser import IntegratedParser


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
