"""
Integrated Parsing Strategy

Uses the new integrated parser system.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from src.parsers.parser import IntegratedParser, ParsedBook

from .parsing import ParsingStrategy


class IntegratedParsingStrategy(ParsingStrategy):
    """
    Parsing strategy using the new integrated parser.

    This replaces the simplified StandardParsingStrategy with a robust
    parser that handles Gutenberg texts, multiple formats, and
    hierarchical structures.
    """

    def __init__(self):
        """Initialize the integrated parsing strategy."""
        self.parser = IntegratedParser()

    async def execute_async(self, data: Any) -> Any:
        """Execute parsing strategy."""
        if isinstance(data, str):
            return await self.parse_async(data, None)
        elif isinstance(data, dict):
            raw_data = data.get("text", "")
            format_hint = data.get("format", None)
            return await self.parse_async(raw_data, format_hint)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

    async def detect_format_async(self, text: str) -> str:
        """
        Detect text format using the integrated detector.

        Returns format as string for compatibility.
        """
        # Run synchronous detection in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._detect_format_sync, text)
        return result

    def _detect_format_sync(self, text: str) -> str:
        """Synchronous format detection."""
        # Parse with no format hint to let detector work
        parsed = self.parser.parse(text)
        return parsed.format.value

    async def parse_async(self, raw_data: str, format_type: Optional[str] = None) -> dict[str, Any]:
        """
        Parse raw text into structured format.

        Args:
            raw_data: Raw text content (possibly with Gutenberg headers)
            format_type: Optional format hint

        Returns:
            Parsed book data as dictionary
        """
        # Run synchronous parsing in executor
        loop = asyncio.get_event_loop()
        parsed_book = await loop.run_in_executor(None, self.parser.parse, raw_data, format_type)

        # Convert ParsedBook to dictionary format expected by service
        return self._convert_to_dict(parsed_book)

    def _convert_to_dict(self, parsed_book: ParsedBook) -> dict[str, Any]:
        """
        Convert ParsedBook to dictionary format.

        This maintains compatibility with the existing service interface.
        """
        return {
            "title": parsed_book.title,
            "author": parsed_book.author,
            "chapters": parsed_book.chapters,
            "metadata": parsed_book.metadata,
            "format": parsed_book.format.value,
            "format_confidence": parsed_book.format_confidence,
            "stats": {
                "raw_length": parsed_book.raw_text_length,
                "cleaned_length": parsed_book.cleaned_text_length,
                "chapters": len(parsed_book.chapters),
                "total_paragraphs": sum(len(ch["paragraphs"]) for ch in parsed_book.chapters),
            },
        }

    def parse_sync(self, raw_data: str, format_type: Optional[str] = None) -> dict[str, Any]:
        """
        Synchronous parsing for convenience.

        Args:
            raw_data: Raw text content
            format_type: Optional format hint

        Returns:
            Parsed book data as dictionary
        """
        parsed_book = self.parser.parse(raw_data, format_type)
        return self._convert_to_dict(parsed_book)
