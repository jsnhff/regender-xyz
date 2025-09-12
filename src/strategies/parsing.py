"""
Parsing Strategy Classes

This module defines strategies for parsing different book formats.
"""

from abc import abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

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


class StandardParsingStrategy(ParsingStrategy):
    """
    Standard parsing strategy using the existing parser.

    This wraps the existing book_parser module for backward compatibility.
    """

    def __init__(self):
        """Initialize the standard parsing strategy."""
        self.chapter_patterns = [r"^Chapter\s+\d+", r"^CHAPTER\s+[IVX]+", r"^\d+\.", r"^Part\s+\d+"]

    async def execute_async(self, data: Any) -> Any:
        """Execute parsing strategy."""
        if isinstance(data, str):
            format_type = await self.detect_format_async(data)
            return await self.parse_async(data, format_type)
        elif isinstance(data, dict):
            raw_data = data.get("text", "")
            format_type = data.get("format", await self.detect_format_async(raw_data))
            return await self.parse_async(raw_data, format_type)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

    async def detect_format_async(self, text: str) -> str:
        """Detect text format."""
        import re

        # Simple format detection
        lines = text.split("\n")[:100]  # Check first 100 lines
        text_sample = "\n".join(lines).lower()

        # Check for play format
        if "dramatis personae" in text_sample or re.search(r"act\s+[ivx]", text_sample):
            return "play"

        # Check for chapters
        if "chapter" in text_sample:
            return "standard"

        # Check for multi-part
        if "part " in text_sample or "book " in text_sample:
            return "multi_part"

        return "standard"

    async def parse_async(self, raw_data: str, format_type: str) -> dict[str, Any]:
        """Parse raw text into structured format."""
        import re

        lines = raw_data.split("\n")
        chapters = []
        current_chapter = None
        current_paragraphs = []

        for line in lines:
            # Check if line is a chapter header
            is_chapter = any(re.match(pattern, line.strip()) for pattern in self.chapter_patterns)

            if is_chapter:
                # Save previous chapter
                if current_chapter and current_paragraphs:
                    chapters.append({"title": current_chapter, "paragraphs": current_paragraphs})
                current_chapter = line.strip()
                current_paragraphs = []
            elif line.strip():  # Non-empty line
                current_paragraphs.append(line.strip())

        # Save last chapter
        if current_chapter and current_paragraphs:
            chapters.append({"title": current_chapter, "paragraphs": current_paragraphs})

        # If no chapters found, treat as single chapter
        if not chapters and lines:
            chapters = [
                {
                    "title": "Chapter 1",
                    "paragraphs": [line.strip() for line in lines if line.strip()],
                }
            ]

        return {"chapters": chapters, "metadata": {"format": format_type}}


class PlayParsingStrategy(ParsingStrategy):
    """Specialized strategy for parsing plays."""

    async def execute_async(self, data: Any) -> Any:
        """Execute play parsing strategy."""
        if isinstance(data, str):
            return await self.parse_async(data, "play")
        else:
            raise ValueError("Play parser requires string input")

    async def detect_format_async(self, text: str) -> str:
        """Detect if text is a play."""
        import re

        text_lower = text[:5000].lower()  # Check first 5000 chars
        if "dramatis personae" in text_lower or re.search(r"act\s+[ivx]", text_lower):
            return "play"
        return "unknown"

    async def parse_async(self, raw_data: str, format_type: str) -> dict[str, Any]:
        """Parse play text."""
        import re

        lines = raw_data.split("\n")
        chapters = []
        current_act = None
        current_scene = None
        current_paragraphs = []

        # Simple play parsing patterns
        act_pattern = re.compile(r"^(ACT|Act)\s+([IVX]+|\d+)", re.IGNORECASE)
        scene_pattern = re.compile(r"^(SCENE|Scene)\s+([ivx]+|\d+)", re.IGNORECASE)

        for line in lines:
            act_match = act_pattern.match(line.strip())
            scene_match = scene_pattern.match(line.strip())

            if act_match:
                # Save previous scene
                if current_scene and current_paragraphs:
                    chapters.append(
                        {
                            "title": f"{current_act} - {current_scene}",
                            "paragraphs": current_paragraphs,
                        }
                    )
                    current_paragraphs = []

                current_act = line.strip()
                current_scene = None

            elif scene_match:
                # Save previous scene
                if current_scene and current_paragraphs:
                    chapters.append(
                        {
                            "title": f"{current_act} - {current_scene}"
                            if current_act
                            else current_scene,
                            "paragraphs": current_paragraphs,
                        }
                    )
                    current_paragraphs = []

                current_scene = line.strip()

            elif line.strip():
                # Add as dialogue or stage direction
                current_paragraphs.append({"sentences": [line.strip()]})

        # Save last scene
        if current_paragraphs:
            title = ""
            if current_act and current_scene:
                title = f"{current_act} - {current_scene}"
            elif current_act:
                title = current_act
            elif current_scene:
                title = current_scene

            chapters.append({"title": title, "paragraphs": current_paragraphs})

        return {"metadata": {"format": "play"}, "chapters": chapters}
