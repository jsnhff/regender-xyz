"""
Text Export Service

Handles exporting books to clean text format with proper Unicode normalization.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from src.models.book import Book
from src.services.base import BaseService, ServiceConfig


class TextExportService(BaseService):
    """
    Service for exporting books to text format.

    Features:
    - Unicode to ASCII normalization
    - Clean text output
    - Configurable text simplification
    - Smart encoding handling
    """

    def __init__(
        self,
        config: ServiceConfig,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize text export service.

        Args:
            config: Service configuration
            logger: Optional logger instance
        """
        super().__init__(config, logger)

        # Try to import text normalization libraries
        self.unidecode = None
        self.ftfy = None

        try:
            import unidecode
            self.unidecode = unidecode
            self.logger.info("Using unidecode for text normalization")
        except ImportError:
            self.logger.debug("unidecode not available")

        try:
            import ftfy
            self.ftfy = ftfy
            self.logger.info("Using ftfy for text fixing")
        except ImportError:
            self.logger.debug("ftfy not available")

        # Configuration options
        self.use_unicode = getattr(config, "preserve_unicode", False)
        self.normalize_method = getattr(config, "normalize_method", "unidecode")  # unidecode, ftfy, or basic

        self.logger.info(f"Initialized {self.__class__.__name__}")

    def simplify_text(self, text: str) -> str:
        """
        Simplify Unicode characters using the best available method.

        Args:
            text: Text to simplify

        Returns:
            Simplified text
        """
        if not text:
            return text

        # First, fix common issues if ftfy is available
        if self.ftfy:
            text = self.ftfy.fix_text(text)

        # If preserving unicode, just fix encoding issues
        if self.use_unicode:
            return text

        # Use the configured normalization method
        if self.normalize_method == "unidecode" and self.unidecode:
            # Unidecode converts unicode to closest ASCII equivalent
            return self.unidecode.unidecode(text)

        elif self.normalize_method == "ftfy" and self.ftfy:
            # Just use ftfy's fixes without full ASCII conversion
            # Still need to handle some problematic characters
            text = self._apply_smart_replacements(text)
            return text

        else:
            # Fallback to basic normalization
            return self._basic_normalize(text)

    def _apply_smart_replacements(self, text: str) -> str:
        """
        Apply smart replacements for common problematic characters.

        Args:
            text: Text to process

        Returns:
            Text with replacements applied
        """
        # Smart replacements that preserve meaning
        replacements = {
            '\u2019': "'",  # Right single quotation mark → apostrophe
            '\u2018': "'",  # Left single quotation mark → apostrophe
            '\u201C': '"',  # Left double quotation mark → regular quote
            '\u201D': '"',  # Right double quotation mark → regular quote
            '\u2014': "--",  # Em dash → double hyphen
            '\u2013': "-",   # En dash → hyphen
            '\u2026': "...", # Ellipsis → three dots
            '\u00A0': " ",   # Non-breaking space → regular space
            '\u2009': " ",   # Thin space → regular space
            '\u2002': " ",   # En space → regular space
            '\u2003': " ",   # Em space → regular space
            '\u200B': "",    # Zero-width space → remove
            '\u00AD': "",    # Soft hyphen → remove
            '\uFEFF': "",    # Zero-width no-break space → remove
            '\u00B4': "'",   # Acute accent → apostrophe
            '\u0060': "'",   # Grave accent → apostrophe
            '\u00A9': "(c)", # Copyright symbol
            '\u00AE': "(R)", # Registered trademark
            '\u2122': "(TM)", # Trademark symbol
            '\u00BC': "1/4", # One quarter
            '\u00BD': "1/2", # One half
            '\u00BE': "3/4", # Three quarters
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        return text

    def _basic_normalize(self, text: str) -> str:
        """
        Basic ASCII normalization without external libraries.

        Args:
            text: Text to normalize

        Returns:
            ASCII-normalized text
        """
        import unicodedata

        # Apply smart replacements first
        text = self._apply_smart_replacements(text)

        # Normalize using Python's built-in unicodedata
        # NFKD = compatibility decomposition
        text = unicodedata.normalize('NFKD', text)

        # Keep only ASCII characters
        ascii_text = []
        for char in text:
            if ord(char) < 128:
                ascii_text.append(char)
            else:
                # Try to get a name-based replacement
                try:
                    name = unicodedata.name(char, '')
                    if 'LATIN' in name and 'LETTER' in name:
                        # Skip combining marks
                        if 'COMBINING' not in name:
                            ascii_text.append('?')
                except:
                    pass

        return ''.join(ascii_text)

    async def process(self, book: Book) -> str:
        """
        Export a book to text format.

        Args:
            book: Book to export

        Returns:
            Exported text content
        """
        lines = []

        # Add title and metadata
        if book.title:
            title = self.simplify_text(book.title)
            lines.append(title)
            lines.append('=' * len(title))
            lines.append('')

        if book.author:
            lines.append(f"Author: {self.simplify_text(book.author)}")
            lines.append('')

        # Process chapters
        for chapter_num, chapter in enumerate(book.chapters, 1):
            # Add chapter title
            if chapter.title:
                chapter_title = self.simplify_text(chapter.title)
            else:
                chapter_title = f"Chapter {chapter_num}"

            lines.append('')
            lines.append(chapter_title)
            lines.append('-' * len(chapter_title))
            lines.append('')

            # Add paragraphs
            for paragraph in chapter.paragraphs:
                para_text = paragraph.get_text()
                cleaned_text = self.simplify_text(para_text)

                if cleaned_text.strip():
                    lines.append(cleaned_text)
                    lines.append('')  # Empty line between paragraphs

        return '\n'.join(lines)

    def export_to_file(self, book: Book, output_path: str) -> str:
        """
        Export a book to a text file.

        Args:
            book: Book to export
            output_path: Path for output file

        Returns:
            Path to created file
        """
        import asyncio

        # Get text content
        loop = asyncio.get_event_loop()
        text_content = loop.run_until_complete(self.process_async(book))

        # Write to file
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path_obj, 'w', encoding='utf-8') as f:
            f.write(text_content)

        self.logger.info(f"Exported text to: {output_path_obj}")
        self.logger.info(f"File size: {output_path_obj.stat().st_size:,} bytes")

        return str(output_path_obj)

    def export_json_to_text(self, json_path: str, output_path: Optional[str] = None) -> str:
        """
        Export a book JSON file to text format.

        This provides backward compatibility with the standalone script.

        Args:
            json_path: Path to book JSON file
            output_path: Optional output path

        Returns:
            Path to created text file
        """
        import json
        from src.models.book import Book

        # Load JSON
        json_path_obj = Path(json_path)
        with open(json_path_obj, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Create Book object from JSON
        book = Book.from_dict(data)

        # Determine output path
        if output_path is None:
            output_path = str(json_path_obj.with_suffix('.txt'))

        return self.export_to_file(book, output_path)