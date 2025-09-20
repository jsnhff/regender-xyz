"""
Analysis Strategy Classes

This module defines strategies for character analysis.
"""

from abc import abstractmethod
from typing import Any, Optional

from src.models.book import Book
from src.utils.token_manager import TokenManager

from .base import Strategy


class AnalysisStrategy(Strategy):
    """Base class for character analysis strategies."""

    @abstractmethod
    async def chunk_book_async(self, book: Book) -> list[str]:
        """
        Chunk book into analyzable pieces.

        Args:
            book: Book to chunk

        Returns:
            List of text chunks
        """
        pass

    @abstractmethod
    async def analyze_chunk_async(self, chunk: str, chunk_index: int) -> dict[str, Any]:
        """
        Analyze a single chunk for characters.

        Args:
            chunk: Text chunk to analyze
            chunk_index: Index of the chunk

        Returns:
            Character analysis results
        """
        pass


class SmartChunkingStrategy(AnalysisStrategy):
    """
    Smart chunking strategy that respects chapter boundaries.

    This wraps the existing smart chunking logic.
    """

    def __init__(self, max_tokens: int = 4000, token_manager: Optional[TokenManager] = None):
        """
        Initialize smart chunking strategy.

        Args:
            max_tokens: Maximum tokens per chunk
            token_manager: Token manager for consistent estimation
        """
        self.max_tokens = max_tokens
        self.token_manager = token_manager or TokenManager()

    async def execute_async(self, data: Any) -> Any:
        """Execute analysis strategy."""
        if isinstance(data, Book):
            chunks = await self.chunk_book_async(data)
            results = []
            for i, chunk in enumerate(chunks):
                result = await self.analyze_chunk_async(chunk, i)
                results.append(result)
            return results
        else:
            raise ValueError("SmartChunkingStrategy requires Book input")

    async def chunk_book_async(self, book: Book) -> list[str]:
        """Chunk book intelligently using TokenManager."""

        chunks = []
        current_chunk = []
        current_tokens = 0

        for chapter in book.chapters:
            chapter_text = chapter.get_text()
            chapter_tokens = self.token_manager.estimate_tokens(chapter_text)

            # If single chapter is too large, split it
            if chapter_tokens > self.max_tokens:
                # Save current chunk if any
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Use TokenManager's intelligent chunking for large chapters
                chapter_chunks = self.token_manager.chunk_text(
                    chapter_text,
                    max_tokens=self.max_tokens,
                    preserve_boundaries=True
                )

                # Extract text from TextChunk objects
                for text_chunk in chapter_chunks:
                    chunks.append(text_chunk.text)
                continue

            # If adding chapter would exceed limit, start new chunk
            elif current_tokens + chapter_tokens > self.max_tokens:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                current_chunk.append(chapter_text)
                current_tokens = chapter_tokens

            # Add chapter to current chunk
            else:
                current_chunk.append(chapter_text)
                current_tokens += chapter_tokens

        # Add remaining chunk
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    async def analyze_chunk_async(self, chunk: str, chunk_index: int) -> dict[str, Any]:
        """Analyze a chunk (placeholder - actual implementation would use LLM)."""
        # This would be implemented with actual LLM calls
        # For now, return placeholder
        return {"chunk_index": chunk_index, "characters": [], "text_length": len(chunk)}


class SequentialStrategy(AnalysisStrategy):
    """Sequential chapter-by-chapter analysis."""

    async def execute_async(self, data: Any) -> Any:
        """Execute sequential analysis."""
        if isinstance(data, Book):
            chunks = await self.chunk_book_async(data)
            results = []
            for i, chunk in enumerate(chunks):
                result = await self.analyze_chunk_async(chunk, i)
                results.append(result)
            return results
        else:
            raise ValueError("SequentialStrategy requires Book input")

    async def chunk_book_async(self, book: Book) -> list[str]:
        """Create one chunk per chapter."""
        return [chapter.get_text() for chapter in book.chapters]

    async def analyze_chunk_async(self, chunk: str, chunk_index: int) -> dict[str, Any]:
        """Analyze a chapter."""
        return {"chunk_index": chunk_index, "characters": [], "text_length": len(chunk)}


class RateLimitedStrategy(AnalysisStrategy):
    """Rate-limited analysis for API constraints."""

    def __init__(self, requests_per_minute: int = 5, token_manager: Optional[TokenManager] = None):
        """
        Initialize rate-limited strategy.

        Args:
            requests_per_minute: API rate limit
            token_manager: Token manager for consistent estimation
        """
        self.requests_per_minute = requests_per_minute
        self.last_request_time = 0
        self.token_manager = token_manager or TokenManager()

    async def execute_async(self, data: Any) -> Any:
        """Execute rate-limited analysis."""
        if isinstance(data, Book):
            chunks = await self.chunk_book_async(data)
            results = []

            import asyncio
            import time

            min_interval = 60 / self.requests_per_minute

            for i, chunk in enumerate(chunks):
                # Rate limiting
                current_time = time.time()
                elapsed = current_time - self.last_request_time
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)

                result = await self.analyze_chunk_async(chunk, i)
                results.append(result)
                self.last_request_time = time.time()

            return results
        else:
            raise ValueError("RateLimitedStrategy requires Book input")

    async def chunk_book_async(self, book: Book) -> list[str]:
        """Create reasonably sized chunks using TokenManager."""

        # Use smaller chunks for rate-limited analysis
        max_tokens = 2000  # Smaller chunks for rate limiting

        chunks = []
        current_chunk = []
        current_tokens = 0

        for chapter in book.chapters:
            for paragraph in chapter.paragraphs:
                para_text = paragraph.get_text()
                para_tokens = self.token_manager.estimate_tokens(para_text)

                if current_tokens + para_tokens > max_tokens and current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                current_chunk.append(para_text)
                current_tokens += para_tokens

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks

    async def analyze_chunk_async(self, chunk: str, chunk_index: int) -> dict[str, Any]:
        """Analyze with rate limiting."""
        return {"chunk_index": chunk_index, "characters": [], "text_length": len(chunk)}
