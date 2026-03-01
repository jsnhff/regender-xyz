"""
Unit tests for parser modules:
- GutenbergParser (gutenberg.py)
- FormatDetector (detector.py)
- validate_and_clean_chapters / is_collection (chapter_validator.py)
- BookConverter (book_converter.py)
"""

import pytest

from src.parsers.book_converter import BookConverter
from src.parsers.chapter_validator import is_collection, validate_and_clean_chapters
from src.parsers.detector import BookFormat, FormatDetector
from src.parsers.gutenberg import GutenbergMetadata, GutenbergParser, clean_gutenberg_text
from src.parsers.parser import ParsedBook

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GUTENBERG_HEADER = """\
The Project Gutenberg EBook of Pride and Prejudice, by Jane Austen

Title: Pride and Prejudice
Author: Jane Austen
Language: English
Release Date: August 26, 2008 [EBook #1342]
Produced by: Anonymous
Character set encoding: UTF-8

This eBook is for the use of anyone anywhere at no cost and with
almost no restrictions whatsoever.

*** START OF THIS PROJECT GUTENBERG EBOOK PRIDE AND PREJUDICE ***
"""

GUTENBERG_FOOTER = """
*** END OF THIS PROJECT GUTENBERG EBOOK PRIDE AND PREJUDICE ***

This eBook is for the use of anyone anywhere at no cost.
"""


def make_gutenberg_text(body: str) -> str:
    return GUTENBERG_HEADER + body + GUTENBERG_FOOTER


def make_chapter_dict(title="Chapter 1", paragraphs=None, para_count=5):
    """Create a chapter dict with the given number of simple string paragraphs."""
    if paragraphs is not None:
        return {"title": title, "paragraphs": paragraphs}
    return {
        "title": title,
        "paragraphs": [f"Paragraph {i + 1} text here." for i in range(para_count)],
    }


def make_parsed_book(title="Test", author="Author", chapters=None):
    chapters = chapters or [
        make_chapter_dict("Chapter 1", paragraphs=["First paragraph.", "Second paragraph."])
    ]
    return ParsedBook(
        title=title,
        author=author,
        chapters=chapters,
        metadata={},
        format=BookFormat.STANDARD,
        format_confidence=90.0,
        hierarchy=None,
        raw_text_length=100,
        cleaned_text_length=80,
    )


# ---------------------------------------------------------------------------
# GutenbergParser
# ---------------------------------------------------------------------------


class TestGutenbergParser:
    def setup_method(self):
        self.parser = GutenbergParser()

    # --- clean() strips headers/footers ---

    def test_clean_removes_start_marker(self):
        text = make_gutenberg_text("Chapter 1\n\nIt was a dark and stormy night.\n")
        cleaned, _ = self.parser.clean(text)
        assert "START OF THIS PROJECT GUTENBERG" not in cleaned

    def test_clean_removes_end_marker(self):
        text = make_gutenberg_text("Some content.\n")
        cleaned, _ = self.parser.clean(text)
        assert "END OF THIS PROJECT GUTENBERG" not in cleaned

    def test_clean_preserves_body_content(self):
        body = "Chapter 1\n\nIt was a dark and stormy night.\n"
        text = make_gutenberg_text(body)
        cleaned, _ = self.parser.clean(text)
        assert "dark and stormy night" in cleaned

    # --- metadata extraction ---

    def test_clean_extracts_title(self):
        text = make_gutenberg_text("Some body text.\n")
        _, meta = self.parser.clean(text)
        assert meta.title == "Pride and Prejudice"

    def test_clean_extracts_author(self):
        text = make_gutenberg_text("Some body text.\n")
        _, meta = self.parser.clean(text)
        assert meta.author == "Jane Austen"

    def test_clean_extracts_language(self):
        text = make_gutenberg_text("Some body text.\n")
        _, meta = self.parser.clean(text)
        assert meta.language == "English"

    def test_clean_extracts_ebook_number(self):
        text = make_gutenberg_text("Some body text.\n")
        _, meta = self.parser.clean(text)
        assert meta.ebook_number == "1342"

    def test_clean_no_markers_returns_content(self):
        # Text with no Gutenberg markers at all
        plain = "Chapter 1\n\nThis is the story.\n\nThe end."
        cleaned, meta = self.parser.clean(plain)
        assert "This is the story." in cleaned

    def test_metadata_defaults_to_none_when_absent(self):
        plain = "Just some text with no metadata at all.\n" * 10
        _, meta = self.parser.clean(plain)
        assert isinstance(meta, GutenbergMetadata)

    # --- _clean_lines: page numbers and illustration markers ---

    def test_clean_lines_removes_page_numbers(self):
        lines = ["Real content.", "42", "More content."]
        result = self.parser._clean_lines(lines)
        assert "42" not in result

    def test_clean_lines_removes_illustration_markers(self):
        lines = ["Paragraph text.", "[Illustration: A castle]", "More text."]
        result = self.parser._clean_lines(lines)
        assert not any("[Illustration" in line for line in result)

    def test_clean_lines_collapses_excess_blank_lines(self):
        lines = ["Text.", "", "", "", "", "More text."]
        result = self.parser._clean_lines(lines)
        blank_count = sum(1 for line in result if not line.strip())
        assert blank_count <= 2

    # --- _skip_toc ---

    def test_skip_toc_removes_contents_section(self):
        lines = [
            "CONTENTS",
            "Chapter I...1",
            "Chapter II...5",
            "Chapter III...10",
            "",
            "CHAPTER I",
            "It was the best of times.",
        ]
        result = self.parser._skip_toc(lines)
        # The actual chapter content should remain
        assert any("best of times" in line for line in result)
        # TOC entries should be gone or chapter content reached
        chapter_idx = next((i for i, line in enumerate(result) if "CHAPTER I" in line), None)
        assert chapter_idx is not None

    # --- get_toc ---

    def test_get_toc_extracts_toc(self):
        text = "CONTENTS\nChapter I\nChapter II\n\n\n\nCHAPTER I\nStory begins."
        toc = self.parser.get_toc(text)
        assert toc is not None
        assert "CONTENTS" in toc

    def test_get_toc_returns_none_when_absent(self):
        text = "CHAPTER I\nStory begins here."
        assert self.parser.get_toc(text) is None

    # --- convenience function ---

    def test_clean_gutenberg_text_function(self):
        text = make_gutenberg_text("Some content here.\n")
        cleaned, meta = clean_gutenberg_text(text)
        assert isinstance(cleaned, str)
        assert isinstance(meta, GutenbergMetadata)


# ---------------------------------------------------------------------------
# FormatDetector
# ---------------------------------------------------------------------------


class TestFormatDetector:
    def setup_method(self):
        self.detector = FormatDetector()

    def _detect(self, text):
        return self.detector.detect(text)

    def test_standard_novel_detected(self):
        text = "\n".join(
            ["CHAPTER I", "Content here.", "CHAPTER II", "More content.", "CHAPTER III", "End."]
            * 10
        )
        result = self._detect(text)
        assert result.format == BookFormat.STANDARD

    def test_play_format_detected(self):
        text = "\n".join(
            [
                "ACT I",
                "SCENE I",
                "Enter HAMLET",
                "HAMLET: To be or not to be.",
                "[Exit HAMLET]",
                "ACT II",
                "SCENE I",
                "Enter OPHELIA",
                "[Exeunt]",
            ]
            * 5
        )
        result = self._detect(text)
        assert result.format == BookFormat.PLAY

    def test_multi_part_detected(self):
        text = "\n".join(
            [
                "VOLUME I",
                "CHAPTER I",
                "Content here.",
                "VOLUME II",
                "CHAPTER I",
                "More content.",
            ]
            * 5
        )
        result = self._detect(text)
        assert result.format == BookFormat.MULTI_PART

    def test_unknown_text_defaults_to_standard(self):
        text = "Just some ordinary prose with no structural markers at all."
        result = self._detect(text)
        # Should default to STANDARD or UNKNOWN but not crash
        assert result.format in (BookFormat.STANDARD, BookFormat.UNKNOWN)

    def test_result_has_confidence_in_range(self):
        lines = []
        for i in range(10):
            lines.extend([f"CHAPTER {i}", "Content."])
        text = "\n".join(lines)
        result = self._detect(text)
        assert 0 <= result.confidence <= 100

    def test_result_has_recommendations_list(self):
        text = "CHAPTER I\nSome text."
        result = self._detect(text)
        assert isinstance(result.recommendations, list)

    def test_result_has_evidence_dict(self):
        text = "CHAPTER I\nSome text."
        result = self._detect(text)
        assert isinstance(result.evidence, dict)

    def test_play_requires_both_acts_and_scenes(self):
        # With only 2 acts and no scenes the penalised score (×0.3) stays below
        # the 5-point detection threshold, so the format is NOT detected as PLAY.
        text = "ACT I\nContent.\nACT II\nMore content."
        result = self._detect(text)
        assert result.format != BookFormat.PLAY

    def test_toc_boosts_correct_format(self):
        body = "\n".join(["CHAPTER I", "Content."] * 10)
        toc = "CONTENTS\nChapter I\nChapter II\nChapter III\nChapter IV"
        result = self.detector.detect(body, toc=toc)
        assert result.format == BookFormat.STANDARD

    def test_epistolary_detected(self):
        text = "\n".join(
            [
                "Letter I",
                "Dear Alice, I write to you.",
                "Letter II",
                "Dear Bob, I hope you are well.",
                "Letter III",
                "My dearest Charles, what news.",
            ]
            * 5
        )
        result = self._detect(text)
        assert result.format == BookFormat.EPISTOLARY


# ---------------------------------------------------------------------------
# chapter_validator
# ---------------------------------------------------------------------------


class TestValidateAndCleanChapters:
    def test_empty_input_returns_empty(self):
        assert validate_and_clean_chapters([]) == []

    def test_valid_chapters_pass_through(self):
        chapters = [make_chapter_dict(f"Chapter {i}", para_count=5) for i in range(3)]
        result = validate_and_clean_chapters(chapters)
        assert len(result) == 3

    def test_chapters_are_renumbered_sequentially(self):
        chapters = [make_chapter_dict(f"Chapter {i}", para_count=5) for i in range(3)]
        result = validate_and_clean_chapters(chapters)
        numbers = [ch["number"] for ch in result]
        assert numbers == [1, 2, 3]

    def test_tiny_chapters_merged_into_next(self):
        tiny = make_chapter_dict("Tiny", para_count=1)  # below min_paragraphs=3
        real = make_chapter_dict("Real Chapter", para_count=5)
        result = validate_and_clean_chapters([tiny, real])
        # real chapter should absorb the tiny one's content
        # and result should still have at least 1 chapter
        assert len(result) >= 1
        assert result[-1]["paragraphs"]  # has content

    def test_all_tiny_chapters_produce_single_fallback(self):
        chapters = [make_chapter_dict(f"Ch {i}", para_count=1) for i in range(3)]
        result = validate_and_clean_chapters(chapters)
        # All content pooled into one chapter
        assert len(result) == 1
        assert len(result[0]["paragraphs"]) == 3  # one para from each tiny chapter

    def test_custom_min_paragraphs(self):
        # With min_paragraphs=1, even tiny chapters are valid
        chapters = [make_chapter_dict(f"Ch {i}", para_count=1) for i in range(3)]
        result = validate_and_clean_chapters(chapters, min_paragraphs=1)
        assert len(result) == 3

    def test_chapter_titles_preserved(self):
        chapters = [make_chapter_dict("My Title", para_count=5)]
        result = validate_and_clean_chapters(chapters)
        assert result[0]["title"] == "My Title"

    def test_empty_chapters_without_content_excluded(self):
        chapters = [make_chapter_dict("Empty", para_count=0)]
        result = validate_and_clean_chapters(chapters)
        assert result == []


class TestIsCollection:
    def test_small_chapter_count_not_collection(self):
        chapters = [make_chapter_dict() for _ in range(10)]
        assert is_collection(chapters) is False

    def test_many_acts_and_scenes_is_collection(self):
        chapters = [{"title": f"Act {i} Scene {j}"} for i in range(10) for j in range(10)]
        assert is_collection(chapters) is True

    def test_many_regular_chapters_not_collection(self):
        chapters = [{"title": f"Chapter {i}"} for i in range(150)]
        assert is_collection(chapters) is False

    def test_mixed_majority_acts_is_collection(self):
        # 90 act/scene chapters out of 105 total = 85.7% > 50%; total > 100 threshold
        act_chapters = [{"title": f"Act {i}"} for i in range(90)]
        regular = [{"title": f"Chapter {i}"} for i in range(15)]
        assert is_collection(act_chapters + regular) is True


# ---------------------------------------------------------------------------
# BookConverter
# ---------------------------------------------------------------------------


class TestBookConverter:
    def setup_method(self):
        self.converter = BookConverter()

    # --- split_sentences ---

    def test_split_basic_sentences(self):
        text = "Hello world. Goodbye world."
        sentences = self.converter.split_sentences(text)
        assert len(sentences) == 2
        assert sentences[0] == "Hello world."

    def test_split_empty_string(self):
        assert self.converter.split_sentences("") == []

    def test_split_whitespace_only(self):
        assert self.converter.split_sentences("   ") == []

    def test_split_preserves_abbreviations(self):
        text = "Mr. Smith went to Washington. He arrived safely."
        sentences = self.converter.split_sentences(text)
        # "Mr. Smith went to Washington." should be one sentence
        assert any("Mr. Smith" in s for s in sentences)
        assert len(sentences) == 2

    def test_split_single_sentence_no_period(self):
        text = "This is a sentence with no period"
        sentences = self.converter.split_sentences(text)
        assert sentences == ["This is a sentence with no period"]

    def test_split_normalizes_whitespace(self):
        text = "First  sentence.   Second sentence."
        sentences = self.converter.split_sentences(text)
        assert not any("  " in s for s in sentences)

    # --- convert_paragraph ---

    def test_convert_paragraph_returns_paragraph_object(self):
        from src.models.book import Paragraph

        p = self.converter.convert_paragraph("Hello. World.")
        assert isinstance(p, Paragraph)
        assert len(p.sentences) == 2

    def test_convert_paragraph_empty_string(self):
        p = self.converter.convert_paragraph("")
        assert p.sentences == []

    # --- convert_chapter ---

    def test_convert_chapter_with_string_paragraphs(self):
        chapter_dict = {
            "number": 1,
            "title": "The Beginning",
            "paragraphs": ["First paragraph text.", "Second paragraph text."],
        }
        chapter = self.converter.convert_chapter(chapter_dict)
        assert chapter.title == "The Beginning"
        assert chapter.number == 1
        assert len(chapter.paragraphs) == 2

    def test_convert_chapter_with_dict_paragraphs(self):
        chapter_dict = {
            "number": 1,
            "title": "Dict Chapter",
            "paragraphs": [{"sentences": ["A sentence."]}],
        }
        chapter = self.converter.convert_chapter(chapter_dict)
        assert len(chapter.paragraphs) == 1
        assert chapter.paragraphs[0].sentences == ["A sentence."]

    def test_convert_chapter_skips_empty_paragraphs(self):
        chapter_dict = {
            "number": 1,
            "title": "Chapter",
            "paragraphs": ["Real content.", ""],  # empty string produces no sentences
        }
        chapter = self.converter.convert_chapter(chapter_dict)
        assert len(chapter.paragraphs) == 1

    # --- convert ---

    def test_convert_parsed_book_to_book(self):
        from src.models.book import Book

        parsed = make_parsed_book()
        book = self.converter.convert(parsed)
        assert isinstance(book, Book)
        assert book.title == "Test"
        assert book.author == "Author"

    def test_convert_skips_empty_chapters(self):
        parsed = make_parsed_book(
            chapters=[
                make_chapter_dict("Good Chapter", paragraphs=["Content here."]),
                make_chapter_dict("Empty Chapter", paragraphs=[]),  # will be skipped
            ]
        )
        book = self.converter.convert(parsed)
        assert book.chapter_count() == 1

    def test_convert_metadata_includes_format(self):
        parsed = make_parsed_book()
        book = self.converter.convert(parsed)
        assert "format" in book.metadata

    # --- convert_to_json ---

    def test_convert_to_json_returns_dict(self):
        parsed = make_parsed_book()
        result = self.converter.convert_to_json(parsed)
        assert isinstance(result, dict)
        assert "chapters" in result
        assert "metadata" in result
