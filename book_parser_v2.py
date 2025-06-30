#!/usr/bin/env python3
"""
Refined Book Parser v2 - Based on analysis of 100 Gutenberg texts.

This parser handles:
1. Multiple chapter formats (Roman/Arabic numerals, with/without titles)
2. Table of Contents detection and filtering
3. Special sections (Preface, Introduction, etc.)
4. Various book structures (Acts, Books, Parts, Letters)
5. Edge cases found in real books
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SectionType(Enum):
    """Types of book sections."""
    # Metadata sections
    TITLE_PAGE = "title_page"
    TOC = "toc"
    
    # Content sections
    PREFACE = "preface"
    INTRODUCTION = "introduction"
    PROLOGUE = "prologue"
    CHAPTER = "chapter"
    ACT = "act"
    SCENE = "scene"
    BOOK = "book"
    PART = "part"
    LETTER = "letter"
    EPILOGUE = "epilogue"
    APPENDIX = "appendix"
    
    # Other
    NOTES = "notes"
    GLOSSARY = "glossary"
    BIBLIOGRAPHY = "bibliography"
    UNKNOWN = "unknown"


@dataclass
class Section:
    """Represents a section of a book."""
    type: SectionType
    number: Optional[str] = None
    title: Optional[str] = None
    content: str = ""
    start_pos: int = 0
    end_pos: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedBook:
    """Represents a fully parsed book."""
    metadata: Dict[str, Any] = field(default_factory=dict)
    sections: List[Section] = field(default_factory=list)
    
    @property
    def chapters(self) -> List[Section]:
        """Get only chapter sections."""
        return [s for s in self.sections if s.type == SectionType.CHAPTER]
    
    @property
    def content_sections(self) -> List[Section]:
        """Get all content sections (chapters, acts, etc.)."""
        content_types = {
            SectionType.CHAPTER, SectionType.ACT, SectionType.SCENE,
            SectionType.BOOK, SectionType.PART, SectionType.LETTER
        }
        return [s for s in self.sections if s.type in content_types]


class BookParserV2:
    """Refined book parser based on analysis of 100 Gutenberg texts."""
    
    # Chapter patterns ordered by frequency from analysis
    CHAPTER_PATTERNS = [
        # Most common: CHAPTER with Roman numerals
        (r'^CHAPTER\s+([IVXLCDM]+)\.?\s*$', SectionType.CHAPTER, 'roman'),
        (r'^CHAPTER\s+([IVXLCDM]+)\.\s+(.+)$', SectionType.CHAPTER, 'roman_titled'),
        (r'^Chapter\s+([IVXLCDM]+)\.?\s*$', SectionType.CHAPTER, 'roman'),
        (r'^Chapter\s+([IVXLCDM]+)\.\s+(.+)$', SectionType.CHAPTER, 'roman_titled'),
        
        # Bare Roman numerals (common in older texts)
        (r'^([IVXLCDM]+)\.?\s*$', SectionType.CHAPTER, 'bare_roman'),
        
        # Acts (common in plays)
        (r'^ACT\s+([IVXLCDM]+)\.?\s*$', SectionType.ACT, 'roman'),
        (r'^Act\s+([IVXLCDM]+)\.?\s*$', SectionType.ACT, 'roman'),
        
        # Arabic numerals
        (r'^CHAPTER\s+(\d+)\.?\s*$', SectionType.CHAPTER, 'arabic'),
        (r'^CHAPTER\s+(\d+)\.\s+(.+)$', SectionType.CHAPTER, 'arabic_titled'),
        (r'^Chapter\s+(\d+)\.?\s*$', SectionType.CHAPTER, 'arabic'),
        (r'^Chapter\s+(\d+)\.\s+(.+)$', SectionType.CHAPTER, 'arabic_titled'),
        (r'^(\d+)\.?\s*$', SectionType.CHAPTER, 'bare_arabic'),
        
        # Books and Parts
        (r'^BOOK\s+([IVXLCDM]+)\.?\s*$', SectionType.BOOK, 'roman'),
        (r'^BOOK\s+(\d+)\.?\s*$', SectionType.BOOK, 'arabic'),
        (r'^PART\s+([IVXLCDM]+)\.?\s*$', SectionType.PART, 'roman'),
        (r'^PART\s+(\d+)\.?\s*$', SectionType.PART, 'arabic'),
        
        # Letters (epistolary novels)
        (r'^LETTER\s+([IVXLCDM]+)\.?\s*$', SectionType.LETTER, 'roman'),
        (r'^LETTER\s+(\d+)\.?\s*$', SectionType.LETTER, 'arabic'),
        
        # Scenes
        (r'^SCENE\s+([IVXLCDM]+)\.?\s*$', SectionType.SCENE, 'roman'),
        (r'^Scene\s+([IVXLCDM]+)\.?\s*$', SectionType.SCENE, 'roman'),
        
        # With separators (: or -)
        (r'^CHAPTER\s+([IVXLCDM]+)\s*[:—-]\s*(.*)$', SectionType.CHAPTER, 'roman_sep'),
        (r'^CHAPTER\s+(\d+)\s*[:—-]\s*(.*)$', SectionType.CHAPTER, 'arabic_sep'),
    ]
    
    # TOC patterns from analysis
    TOC_PATTERNS = [
        r'^Contents\.?$',
        r'^CONTENTS\.?$',
        r'^contents\.?$',
        r'^TABLE OF CONTENTS\.?$',
        r'^Table of Contents\.?$',
        r'^INDEX\.?$',
        r'^CHAPTER\.?$',  # Sometimes just "CHAPTER" or "CHAPTERS"
    ]
    
    # Special section patterns
    SPECIAL_PATTERNS = {
        'PREFACE': SectionType.PREFACE,
        'INTRODUCTION': SectionType.INTRODUCTION,
        'PROLOGUE': SectionType.PROLOGUE,
        'EPILOGUE': SectionType.EPILOGUE,
        'APPENDIX': SectionType.APPENDIX,
        'NOTES': SectionType.NOTES,
        'GLOSSARY': SectionType.GLOSSARY,
        'BIBLIOGRAPHY': SectionType.BIBLIOGRAPHY,
    }
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize parser.
        
        Args:
            strict_mode: If True, only accept chapters with substantial content
        """
        self.strict_mode = strict_mode
    
    def parse(self, text: str) -> ParsedBook:
        """
        Parse a book text into structured sections.
        
        Args:
            text: Raw book text
            
        Returns:
            ParsedBook object with all sections
        """
        # Clean up text
        text = self._normalize_text(text)
        
        # Extract main content (remove Gutenberg headers/footers)
        content_start, content_end = self._find_content_boundaries(text)
        
        # Extract metadata
        metadata = self._extract_metadata(text[:content_start])
        
        # Find all potential sections
        sections = self._find_sections(text, content_start, content_end)
        
        # Filter and validate sections
        sections = self._validate_sections(sections, text)
        
        # Sort sections properly
        sections = self._sort_sections(sections)
        
        # Create parsed book
        book = ParsedBook(metadata=metadata, sections=sections)
        
        # Log summary
        logger.info(f"Parsed book: {metadata.get('title', 'Unknown')}")
        logger.info(f"Found {len(book.chapters)} chapters, {len(sections)} total sections")
        
        return book
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text encoding and line endings."""
        # Remove BOM
        if text.startswith('\ufeff'):
            text = text[1:]
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Fix common encoding issues
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace('—', '--')
        
        return text
    
    def _find_content_boundaries(self, text: str) -> Tuple[int, int]:
        """Find the main content boundaries (excluding Gutenberg boilerplate)."""
        start = 0
        end = len(text)
        
        # Look for standard Gutenberg markers
        start_patterns = [
            r'\*\*\*\s*START[^\*]+\*\*\*',
            r'\*\*\*START[^\*]+\*\*\*',
            r'END OF THE PROJECT GUTENBERG LICENSE',
        ]
        
        end_patterns = [
            r'\*\*\*\s*END[^\*]+\*\*\*',
            r'\*\*\*END[^\*]+\*\*\*',
            r'End of the Project Gutenberg',
        ]
        
        for pattern in start_patterns:
            match = re.search(pattern, text)
            if match:
                start = match.end()
                break
        
        for pattern in end_patterns:
            match = re.search(pattern, text[start:])
            if match:
                end = start + match.start()
                break
        
        return start, end
    
    def _extract_metadata(self, header_text: str) -> Dict[str, Any]:
        """Extract metadata from header."""
        metadata = {}
        
        # Title patterns
        title_match = re.search(r'Title:\s*(.+)', header_text)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        else:
            # Try alternate pattern
            ebook_match = re.search(r"Project Gutenberg(?:'s|'s)?\s+(?:EBook|eBook|Etext)\s+of\s+(.+?)(?:,|\n|$)", 
                                  header_text, re.IGNORECASE)
            if ebook_match:
                metadata['title'] = ebook_match.group(1).strip()
        
        # Author
        author_match = re.search(r'Author:\s*(.+)', header_text)
        if author_match:
            metadata['author'] = author_match.group(1).strip()
        else:
            # Try "by" pattern
            by_match = re.search(r'by\s+([A-Z][^,\n]+)', header_text)
            if by_match:
                metadata['author'] = by_match.group(1).strip()
        
        # Release date
        date_match = re.search(r'Release Date:\s*(.+)', header_text)
        if date_match:
            metadata['release_date'] = date_match.group(1).strip()
        
        # Language
        lang_match = re.search(r'Language:\s*(.+)', header_text)
        if lang_match:
            metadata['language'] = lang_match.group(1).strip()
        
        return metadata
    
    def _find_sections(self, text: str, start: int, end: int) -> List[Section]:
        """Find all sections in the text."""
        sections = []
        content = text[start:end]
        
        # Find TOC sections
        toc_sections = self._find_toc_sections(content, start)
        sections.extend(toc_sections)
        
        # Find special sections
        special_sections = self._find_special_sections(content, start)
        sections.extend(special_sections)
        
        # Find content sections (chapters, acts, etc.)
        content_sections = self._find_content_sections(content, start)
        sections.extend(content_sections)
        
        # Remove duplicates and sort by position
        sections = self._deduplicate_sections(sections)
        sections.sort(key=lambda s: s.start_pos)
        
        # Fill in content for each section
        for i, section in enumerate(sections):
            if i + 1 < len(sections):
                section.end_pos = sections[i + 1].start_pos
            else:
                section.end_pos = end
            
            section.content = text[section.start_pos:section.end_pos].strip()
        
        return sections
    
    def _find_toc_sections(self, text: str, offset: int) -> List[Section]:
        """Find table of contents sections."""
        sections = []
        
        for pattern in self.TOC_PATTERNS:
            for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
                section = Section(
                    type=SectionType.TOC,
                    title=match.group(0).strip(),
                    start_pos=match.start() + offset
                )
                sections.append(section)
        
        return sections
    
    def _find_special_sections(self, text: str, offset: int) -> List[Section]:
        """Find special sections like PREFACE, INTRODUCTION, etc."""
        sections = []
        
        for keyword, section_type in self.SPECIAL_PATTERNS.items():
            # Look for standalone keywords
            pattern = rf'^{keyword}\.?\s*$'
            for match in re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE):
                section = Section(
                    type=section_type,
                    title=match.group(0).strip(),
                    start_pos=match.start() + offset
                )
                sections.append(section)
        
        return sections
    
    def _find_content_sections(self, text: str, offset: int) -> List[Section]:
        """Find content sections (chapters, acts, etc.)."""
        sections = []
        
        for pattern_str, section_type, pattern_name in self.CHAPTER_PATTERNS:
            pattern = re.compile(pattern_str, re.MULTILINE)
            
            for match in pattern.finditer(text):
                # Extract number and title
                groups = match.groups()
                number = groups[0] if groups else None
                title = groups[1] if len(groups) > 1 else None
                
                # Create section
                section = Section(
                    type=section_type,
                    number=number,
                    title=title or match.group(0).strip(),
                    start_pos=match.start() + offset,
                    metadata={'pattern': pattern_name}
                )
                sections.append(section)
        
        return sections
    
    def _deduplicate_sections(self, sections: List[Section]) -> List[Section]:
        """Remove duplicate sections at the same position."""
        seen_positions = {}
        deduped = []
        
        for section in sections:
            if section.start_pos not in seen_positions:
                seen_positions[section.start_pos] = section
                deduped.append(section)
            else:
                # Keep the more specific section type
                existing = seen_positions[section.start_pos]
                if section.type == SectionType.CHAPTER and existing.type != SectionType.CHAPTER:
                    seen_positions[section.start_pos] = section
                    deduped[deduped.index(existing)] = section
        
        return deduped
    
    def _validate_sections(self, sections: List[Section], text: str) -> List[Section]:
        """Validate and filter sections."""
        validated = []
        
        # Find TOC boundaries
        toc_ranges = self._find_toc_ranges(sections)
        
        for section in sections:
            # Skip sections within TOC
            if self._is_in_toc(section, toc_ranges):
                continue
            
            # In strict mode, validate content sections
            if self.strict_mode and section.type in {SectionType.CHAPTER, SectionType.ACT}:
                if not self._has_substantial_content(section, text):
                    continue
            
            validated.append(section)
        
        return validated
    
    def _find_toc_ranges(self, sections: List[Section]) -> List[Tuple[int, int]]:
        """Find the ranges covered by TOC sections."""
        ranges = []
        
        for section in sections:
            if section.type == SectionType.TOC:
                # TOC typically ends when we hit substantial content
                toc_end = section.end_pos
                
                # Look for the first content section after TOC
                for other in sections:
                    if (other.start_pos > section.start_pos and 
                        other.type in {SectionType.CHAPTER, SectionType.ACT} and
                        self._has_substantial_content(other, section.content)):
                        toc_end = other.start_pos
                        break
                
                ranges.append((section.start_pos, toc_end))
        
        return ranges
    
    def _is_in_toc(self, section: Section, toc_ranges: List[Tuple[int, int]]) -> bool:
        """Check if a section is within a TOC range."""
        for start, end in toc_ranges:
            if start <= section.start_pos < end:
                return True
        return False
    
    def _has_substantial_content(self, section: Section, text: str) -> bool:
        """Check if a section has substantial content."""
        # Get content after section header
        content = section.content
        lines = content.split('\n')
        
        # Skip the header lines
        if len(lines) > 2:
            content_after_header = '\n'.join(lines[2:]).strip()
            
            # Check for substantial content
            if len(content_after_header) > 200:
                # Check it's not just more chapter listings
                if not re.match(r'^(CHAPTER|Chapter|ACT|SCENE)', content_after_header):
                    return True
        
        return False
    
    def _sort_sections(self, sections: List[Section]) -> List[Section]:
        """Sort sections in reading order."""
        # Separate by type
        special_sections = [s for s in sections if s.type in {
            SectionType.PREFACE, SectionType.INTRODUCTION, SectionType.PROLOGUE
        }]
        
        content_sections = [s for s in sections if s.type in {
            SectionType.CHAPTER, SectionType.ACT, SectionType.BOOK, 
            SectionType.PART, SectionType.LETTER
        }]
        
        end_sections = [s for s in sections if s.type in {
            SectionType.EPILOGUE, SectionType.APPENDIX, SectionType.NOTES,
            SectionType.GLOSSARY, SectionType.BIBLIOGRAPHY
        }]
        
        other_sections = [s for s in sections if s not in special_sections + content_sections + end_sections]
        
        # Sort content sections by number if possible
        content_sections = self._sort_by_number(content_sections)
        
        # Combine in reading order
        return other_sections + special_sections + content_sections + end_sections
    
    def _sort_by_number(self, sections: List[Section]) -> List[Section]:
        """Sort sections by their number."""
        def get_sort_key(section: Section) -> Tuple[int, int]:
            if not section.number:
                return (999999, section.start_pos)
            
            # Try to convert to number
            try:
                # Arabic numeral
                return (int(section.number), section.start_pos)
            except ValueError:
                # Try Roman numeral
                try:
                    return (self._roman_to_int(section.number), section.start_pos)
                except:
                    return (999999, section.start_pos)
        
        return sorted(sections, key=get_sort_key)
    
    def _roman_to_int(self, roman: str) -> int:
        """Convert Roman numeral to integer."""
        values = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50,
            'C': 100, 'D': 500, 'M': 1000
        }
        
        total = 0
        prev_value = 0
        
        for char in reversed(roman.upper()):
            value = values.get(char, 0)
            if value < prev_value:
                total -= value
            else:
                total += value
            prev_value = value
        
        return total


def parse_book(filepath: str, strict_mode: bool = False) -> ParsedBook:
    """
    Convenience function to parse a book file.
    
    Args:
        filepath: Path to the book text file
        strict_mode: Whether to use strict validation
        
    Returns:
        ParsedBook object
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    
    parser = BookParserV2(strict_mode=strict_mode)
    return parser.parse(text)


def save_parsed_book(book: ParsedBook, output_file: str):
    """Save parsed book to JSON."""
    # Convert to serializable format
    data = {
        'metadata': book.metadata,
        'sections': []
    }
    
    for section in book.sections:
        data['sections'].append({
            'type': section.type.value,
            'number': section.number,
            'title': section.title,
            'content': section.content[:200] + '...' if len(section.content) > 200 else section.content,
            'start_pos': section.start_pos,
            'end_pos': section.end_pos,
            'metadata': section.metadata
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python book_parser_v2.py <book_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Parse the book
    book = parse_book(input_file)
    
    # Print summary
    print(f"Title: {book.metadata.get('title', 'Unknown')}")
    print(f"Author: {book.metadata.get('author', 'Unknown')}")
    print(f"Total sections: {len(book.sections)}")
    print(f"Chapters: {len(book.chapters)}")
    print(f"Content sections: {len(book.content_sections)}")
    
    # Save if requested
    if output_file:
        save_parsed_book(book, output_file)
        print(f"\nSaved to: {output_file}")