"""
Convert ParsedBook to canonical Book format with sentence splitting.
"""

import re

from src.models.book import Book, Chapter, Paragraph
from src.parsers.parser import ParsedBook


class BookConverter:
    """Converts ParsedBook to canonical Book format."""

    def __init__(self):
        """Initialize the converter."""
        # Common sentence ending patterns
        self.sentence_endings = re.compile(
            r"(?<=[.!?])\s+(?=[A-Z])|"  # Period/exclamation/question + space + capital
            r"(?<=[.!?])\s*$|"  # Period/exclamation/question at end
            r'(?<=[.!?]["\'"])\s+(?=[A-Z])'  # Quoted sentence ending
        )

        # Common abbreviations that don't end sentences
        self.abbreviations = {
            "Mr.",
            "Mrs.",
            "Ms.",
            "Dr.",
            "Prof.",
            "Sr.",
            "Jr.",
            "Co.",
            "Corp.",
            "Inc.",
            "Ltd.",
            "LLC.",
            "U.S.",
            "U.K.",
            "E.U.",
            "U.N.",
            "a.m.",
            "p.m.",
            "i.e.",
            "e.g.",
            "etc.",
            "vs.",
            "Jan.",
            "Feb.",
            "Mar.",
            "Apr.",
            "Jun.",
            "Jul.",
            "Aug.",
            "Sep.",
            "Sept.",
            "Oct.",
            "Nov.",
            "Dec.",
        }

    def split_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        if not text or not text.strip():
            return []

        # Normalize whitespace
        text = " ".join(text.split())

        # Protect abbreviations by replacing periods with placeholder
        protected_text = text
        for abbrev in self.abbreviations:
            protected_text = protected_text.replace(abbrev, abbrev.replace(".", "<!DOT!>"))

        # Split on sentence boundaries
        sentences = self.sentence_endings.split(protected_text)

        # Restore periods in abbreviations and clean up
        result = []
        for sentence in sentences:
            if sentence and sentence.strip():
                # Restore dots
                sentence = sentence.replace("<!DOT!>", ".")
                sentence = sentence.strip()
                if sentence:
                    result.append(sentence)

        # If no sentences found, return the whole text as one sentence
        if not result:
            return [text.strip()] if text.strip() else []

        return result

    def convert_paragraph(self, para_text: str) -> Paragraph:
        """
        Convert paragraph text to Paragraph object.

        Args:
            para_text: Paragraph text

        Returns:
            Paragraph object with sentences
        """
        sentences = self.split_sentences(para_text)
        return Paragraph(sentences=sentences)

    def convert_chapter(self, chapter_dict: dict) -> Chapter:
        """
        Convert chapter dictionary to Chapter object.

        Args:
            chapter_dict: Chapter dictionary from parser

        Returns:
            Chapter object
        """
        # Extract paragraphs
        paragraphs = []
        for para in chapter_dict.get("paragraphs", []):
            if isinstance(para, str):
                # Convert string paragraph to Paragraph object
                paragraph = self.convert_paragraph(para)
                if paragraph.sentences:  # Only add non-empty paragraphs
                    paragraphs.append(paragraph)
            elif isinstance(para, dict):
                # Already structured - convert
                paragraph = Paragraph.from_dict(para)
                if paragraph.sentences:
                    paragraphs.append(paragraph)

        return Chapter(
            number=chapter_dict.get("number"),
            title=chapter_dict.get("title"),
            paragraphs=paragraphs,
            metadata=chapter_dict.get("metadata", {}),
        )

    def convert(self, parsed_book: ParsedBook) -> Book:
        """
        Convert ParsedBook to canonical Book format.

        Args:
            parsed_book: ParsedBook from parser

        Returns:
            Book object in canonical format
        """
        # Convert chapters
        chapters = []
        for chapter_dict in parsed_book.chapters:
            chapter = self.convert_chapter(chapter_dict)
            if chapter.paragraphs:  # Only add non-empty chapters
                chapters.append(chapter)

        # Create Book object
        book = Book(
            title=parsed_book.title,
            author=parsed_book.author,
            chapters=chapters,
            metadata={
                "format": parsed_book.format.value
                if hasattr(parsed_book.format, "value")
                else str(parsed_book.format),
                "format_confidence": parsed_book.format_confidence,
                "original_metadata": parsed_book.metadata,
                "raw_text_length": parsed_book.raw_text_length,
                "cleaned_text_length": parsed_book.cleaned_text_length,
            },
            source_file=None,  # Will be set by caller
        )

        return book

    def convert_to_json(self, parsed_book: ParsedBook) -> dict:
        """
        Convert ParsedBook directly to JSON-serializable dictionary.

        Args:
            parsed_book: ParsedBook from parser

        Returns:
            Dictionary in canonical JSON format
        """
        book = self.convert(parsed_book)
        return book.to_dict()
