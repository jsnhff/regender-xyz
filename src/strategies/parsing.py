"""
Parsing Strategy Classes

This module defines strategies for parsing different book formats.
"""

from abc import abstractmethod
from typing import Dict, Any, List, Optional
from pathlib import Path
from .base import Strategy


class ParsingStrategy(Strategy):
    """Base class for parsing strategies."""
    
    @abstractmethod
    async def parse_async(self, raw_data: str, format_type: str) -> Dict[str, Any]:
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
        self.pattern_registry = None
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Initialize pattern registry."""
        from book_parser.patterns.registry import PatternRegistry
        self.pattern_registry = PatternRegistry()
    
    async def execute_async(self, data: Any) -> Any:
        """Execute parsing strategy."""
        if isinstance(data, str):
            format_type = await self.detect_format_async(data)
            return await self.parse_async(data, format_type)
        elif isinstance(data, dict):
            raw_data = data.get('text', '')
            format_type = data.get('format', await self.detect_format_async(raw_data))
            return await self.parse_async(raw_data, format_type)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
    
    async def detect_format_async(self, text: str) -> str:
        """Detect text format."""
        # Use existing detector logic
        from book_parser.detectors.section_detector import detect_sections
        from book_parser.detectors.play_detector import is_play_format
        
        if is_play_format(text):
            return "play"
        
        sections = detect_sections(text.split('\n'))
        if sections:
            if any('act' in s.lower() or 'scene' in s.lower() for s in sections):
                return "play"
            elif any('chapter' in s.lower() for s in sections):
                return "standard"
            elif any('part' in s.lower() or 'book' in s.lower() for s in sections):
                return "multi_part"
        
        return "standard"
    
    async def parse_async(self, raw_data: str, format_type: str) -> Dict[str, Any]:
        """Parse raw text into structured format."""
        from book_parser.parser import BookParser
        
        # Use existing parser
        parser = BookParser()
        
        # Parse synchronously (existing parser is not async)
        import asyncio
        loop = asyncio.get_event_loop()
        
        # Run in executor to avoid blocking
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(parser.parse_text, raw_data)
            result = await loop.run_in_executor(None, future.result)
        
        return result


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
        from book_parser.detectors.play_detector import is_play_format
        return "play" if is_play_format(text) else "unknown"
    
    async def parse_async(self, raw_data: str, format_type: str) -> Dict[str, Any]:
        """Parse play text."""
        from book_parser.patterns.plays import PlayPattern
        
        pattern = PlayPattern()
        lines = raw_data.split('\n')
        
        # Parse using play pattern
        chapters = []
        current_act = None
        current_scene = None
        current_paragraphs = []
        
        for line in lines:
            if pattern.is_act_header(line):
                # Save previous scene
                if current_scene and current_paragraphs:
                    chapters.append({
                        'title': f"{current_act} - {current_scene}",
                        'paragraphs': current_paragraphs
                    })
                    current_paragraphs = []
                
                current_act = line.strip()
                current_scene = None
                
            elif pattern.is_scene_header(line):
                # Save previous scene
                if current_scene and current_paragraphs:
                    chapters.append({
                        'title': f"{current_act} - {current_scene}" if current_act else current_scene,
                        'paragraphs': current_paragraphs
                    })
                    current_paragraphs = []
                
                current_scene = line.strip()
                
            elif line.strip():
                # Add as dialogue or stage direction
                current_paragraphs.append({
                    'sentences': [line.strip()]
                })
        
        # Save last scene
        if current_paragraphs:
            title = ""
            if current_act and current_scene:
                title = f"{current_act} - {current_scene}"
            elif current_act:
                title = current_act
            elif current_scene:
                title = current_scene
            
            chapters.append({
                'title': title,
                'paragraphs': current_paragraphs
            })
        
        return {
            'metadata': {'format': 'play'},
            'chapters': chapters
        }