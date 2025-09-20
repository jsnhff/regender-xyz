"""
Parsing Strategy Classes

This module defines strategies for parsing different book formats.
"""

from abc import abstractmethod
from typing import Any

from .base import Strategy


class ParsingStrategy(Strategy):
    """Base class for parsing strategies."""

    @abstractmethod
    async def parse_async(self, raw_data: str, format_type: str) -> dict[str, Any]:
        """
        Parse raw text into structured format.

        Args:
            raw_data: Raw text content
            format_type: Detected format type

        Returns:
            Parsed book data as dictionary
        """
        pass

    @abstractmethod
    async def detect_format_async(self, text: str) -> str:
        """
        Detect the format of the text.

        Args:
            text: Text to analyze

        Returns:
            Format identifier
        """
        pass
