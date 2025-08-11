"""
Integrated Parser

Combines all parser components into a complete parsing solution.
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .gutenberg import GutenbergParser
from .detector import FormatDetector, BookFormat
from .hierarchy import HierarchyBuilder, Section, SectionType
from .play import PlayParser, play_to_chapters


@dataclass
class ParsedBook:
    """Result of parsing a book."""
    title: str
    author: Optional[str]
    metadata: Dict[str, Any]
    format: BookFormat
    format_confidence: float
    chapters: List[Dict[str, Any]]
    hierarchy: Optional[Section]
    raw_text_length: int
    cleaned_text_length: int


class IntegratedParser:
    """
    Complete parser that handles the full pipeline:
    1. Clean Gutenberg headers/footers
    2. Detect format
    3. Build hierarchy
    4. Convert to chapters with proper content
    """
    
    def __init__(self):
        """Initialize the integrated parser."""
        self.cleaner = GutenbergParser()
        self.detector = FormatDetector()
        self.builder = HierarchyBuilder()
    
    def parse(self, raw_text: str, format_hint: Optional[str] = None) -> ParsedBook:
        """
        Parse a book from raw text.
        
        Args:
            raw_text: Raw book text (possibly with Gutenberg headers)
            format_hint: Optional hint about format
            
        Returns:
            ParsedBook with all extracted information
        """
        # Step 1: Clean the text
        cleaned_text, metadata = self.cleaner.clean(raw_text)
        
        # Step 2: Detect format
        toc = self.cleaner.get_toc(raw_text)
        detection = self.detector.detect(cleaned_text, toc)
        
        # Use hint if provided and confidence is low
        if format_hint and detection.confidence < 50:
            format_value = format_hint
        else:
            format_value = detection.format.value
        
        # Step 3: Build hierarchy or parse as play
        lines = cleaned_text.split('\n')
        
        # Use specialized play parser for plays (including mixed format with play elements)
        if detection.format == BookFormat.PLAY or \
           (detection.format == BookFormat.MIXED and 'play' in detection.evidence and len(detection.evidence.get('play', [])) > 5):
            play_parser = PlayParser()
            play = play_parser.parse(lines)
            chapters = play_to_chapters(play)
            hierarchy = None  # Play doesn't use hierarchy
        else:
            hierarchy = self.builder.build_hierarchy(lines, format_value, skip_toc=True)
            chapters = None  # Will be converted from hierarchy
        
        # Step 4: Convert to chapters format if not already done
        if chapters is None:
            chapters = self._hierarchy_to_chapters(hierarchy)
        
        # Step 5: Extract title and author from metadata
        title = metadata.title if metadata and metadata.title else 'Unknown Title'
        author = metadata.author if metadata and metadata.author else 'Unknown Author'
        
        return ParsedBook(
            title=title,
            author=author,
            metadata={
                'title': metadata.title if metadata else None,
                'author': metadata.author if metadata else None,
                'language': metadata.language if metadata else None,
                'release_date': metadata.release_date if metadata else None,
                'ebook_number': metadata.ebook_number if metadata else None,
            } if metadata else {},
            format=detection.format,
            format_confidence=detection.confidence,
            chapters=chapters,
            hierarchy=hierarchy,
            raw_text_length=len(raw_text),
            cleaned_text_length=len(cleaned_text)
        )
    
    def _hierarchy_to_chapters(self, hierarchy: Section) -> List[Dict[str, Any]]:
        """
        Convert hierarchical structure to flat chapter list.
        
        Preserves hierarchy information in metadata.
        """
        chapters = []
        chapter_number = 1
        
        def process_section(section: Section, parent_path: List[str] = None):
            nonlocal chapter_number
            
            if parent_path is None:
                parent_path = []
            
            # Skip the root book node
            if section.type == SectionType.BOOK and not parent_path:
                # Process all subsections
                for sub in section.subsections:
                    process_section(sub, parent_path)
                return
            
            # Check if this is a leaf node (has content but no subsections)
            is_leaf = not section.subsections or (
                len(section.content) > 0 and 
                all(len(sub.content) == 0 for sub in section.subsections)
            )
            
            if is_leaf:
                # This is a chapter
                # Convert content lines to paragraphs
                paragraphs = self._lines_to_paragraphs(section.content)
                
                chapter = {
                    'number': chapter_number,
                    'title': section.get_full_title(),
                    'type': section.type.value,
                    'paragraphs': paragraphs,
                    'hierarchy': parent_path.copy() if parent_path else [],
                    'metadata': section.metadata
                }
                
                # Add section number if available
                if section.number:
                    chapter['section_number'] = section.number
                
                chapters.append(chapter)
                chapter_number += 1
            else:
                # This is a container - process subsections
                current_path = parent_path + [section.get_full_title()]
                for sub in section.subsections:
                    process_section(sub, current_path)
        
        process_section(hierarchy)
        return chapters
    
    def _lines_to_paragraphs(self, lines: List[str]) -> List[str]:
        """
        Convert lines to paragraphs.
        
        Groups consecutive non-empty lines into paragraphs.
        """
        paragraphs = []
        current_para = []
        
        for line in lines:
            line = line.rstrip()
            
            if not line:
                # Empty line - end current paragraph
                if current_para:
                    paragraphs.append(' '.join(current_para))
                    current_para = []
            else:
                # Add to current paragraph
                current_para.append(line)
        
        # Don't forget the last paragraph
        if current_para:
            paragraphs.append(' '.join(current_para))
        
        return paragraphs


def parse_book(file_path: str, format_hint: Optional[str] = None) -> ParsedBook:
    """
    Convenience function to parse a book from a file.
    
    Args:
        file_path: Path to the book file
        format_hint: Optional format hint
        
    Returns:
        ParsedBook object
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        raw_text = f.read()
    
    parser = IntegratedParser()
    return parser.parse(raw_text, format_hint)