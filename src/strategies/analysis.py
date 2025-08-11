"""
Analysis Strategy Classes

This module defines strategies for character analysis.
"""

from abc import abstractmethod
from typing import List, Dict, Any, Optional
from .base import Strategy
from src.models.book import Book


class AnalysisStrategy(Strategy):
    """Base class for character analysis strategies."""
    
    @abstractmethod
    async def chunk_book_async(self, book: Book) -> List[str]:
        """
        Chunk book into analyzable pieces.
        
        Args:
            book: Book to chunk
            
        Returns:
            List of text chunks
        """
        pass
    
    @abstractmethod
    async def analyze_chunk_async(self, chunk: str, chunk_index: int) -> Dict[str, Any]:
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
    
    def __init__(self, max_tokens: int = 4000):
        """
        Initialize smart chunking strategy.
        
        Args:
            max_tokens: Maximum tokens per chunk
        """
        self.max_tokens = max_tokens
    
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
    
    async def chunk_book_async(self, book: Book) -> List[str]:
        """Chunk book intelligently."""
        # Simple token estimation (roughly 4 characters per token)
        def estimate_tokens(text: str) -> int:
            return len(text) // 4
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for chapter in book.chapters:
            chapter_text = chapter.get_text()
            chapter_tokens = estimate_tokens(chapter_text)
            
            # If single chapter is too large, split it
            if chapter_tokens > self.max_tokens:
                # Save current chunk if any
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # Split chapter by paragraphs
                for paragraph in chapter.paragraphs:
                    para_text = paragraph.get_text()
                    para_tokens = estimate_tokens(para_text)
                    
                    if current_tokens + para_tokens > self.max_tokens:
                        if current_chunk:
                            chunks.append("\n\n".join(current_chunk))
                            current_chunk = []
                            current_tokens = 0
                    
                    current_chunk.append(para_text)
                    current_tokens += para_tokens
            
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
    
    async def analyze_chunk_async(self, chunk: str, chunk_index: int) -> Dict[str, Any]:
        """Analyze a chunk (placeholder - actual implementation would use LLM)."""
        # This would be implemented with actual LLM calls
        # For now, return placeholder
        return {
            "chunk_index": chunk_index,
            "characters": [],
            "text_length": len(chunk)
        }


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
    
    async def chunk_book_async(self, book: Book) -> List[str]:
        """Create one chunk per chapter."""
        return [chapter.get_text() for chapter in book.chapters]
    
    async def analyze_chunk_async(self, chunk: str, chunk_index: int) -> Dict[str, Any]:
        """Analyze a chapter."""
        return {
            "chunk_index": chunk_index,
            "characters": [],
            "text_length": len(chunk)
        }


class RateLimitedStrategy(AnalysisStrategy):
    """Rate-limited analysis for API constraints."""
    
    def __init__(self, requests_per_minute: int = 5):
        """
        Initialize rate-limited strategy.
        
        Args:
            requests_per_minute: API rate limit
        """
        self.requests_per_minute = requests_per_minute
        self.last_request_time = 0
    
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
    
    async def chunk_book_async(self, book: Book) -> List[str]:
        """Create reasonably sized chunks."""
        # Use smaller chunks for rate-limited analysis
        # Simple token estimation (roughly 4 chars per token)
        def estimate_tokens(text: str) -> int:
            return len(text) // 4
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        max_tokens = 2000  # Smaller chunks for rate limiting
        
        for chapter in book.chapters:
            for paragraph in chapter.paragraphs:
                para_text = paragraph.get_text()
                para_tokens = estimate_tokens(para_text)
                
                if current_tokens + para_tokens > max_tokens and current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                current_chunk.append(para_text)
                current_tokens += para_tokens
        
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        return chunks
    
    async def analyze_chunk_async(self, chunk: str, chunk_index: int) -> Dict[str, Any]:
        """Analyze with rate limiting."""
        return {
            "chunk_index": chunk_index,
            "characters": [],
            "text_length": len(chunk)
        }