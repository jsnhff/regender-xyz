"""
Consolidated Gutenberg Parser

Line-based parser for Project Gutenberg texts.
Avoids regex where possible for better reliability and maintainability.
"""

from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class GutenbergMetadata:
    """Metadata extracted from Gutenberg text."""
    title: Optional[str] = None
    author: Optional[str] = None
    release_date: Optional[str] = None
    language: Optional[str] = None
    ebook_number: Optional[str] = None
    posting_date: Optional[str] = None
    last_updated: Optional[str] = None
    produced_by: Optional[str] = None


class GutenbergParser:
    """
    Line-based Project Gutenberg text parser.
    
    Uses simple string operations instead of regex for robustness.
    """
    
    def clean(self, text: str) -> Tuple[str, GutenbergMetadata]:
        """
        Clean Gutenberg text and extract metadata.
        
        Args:
            text: Raw Gutenberg text
            
        Returns:
            Tuple of (cleaned_text, metadata)
        """
        lines = text.split('\n')
        metadata = GutenbergMetadata()
        
        # Find content boundaries
        start_idx = self._find_start(lines)
        end_idx = self._find_end(lines)
        
        # Extract metadata from header
        if start_idx and start_idx > 0:
            header_lines = lines[:min(start_idx, 500)]
            metadata = self._extract_metadata(header_lines)
        else:
            # No clear start, try first 200 lines anyway
            header_lines = lines[:min(200, len(lines))]
            metadata = self._extract_metadata(header_lines)
        
        # Extract content
        if start_idx is not None and end_idx is not None:
            content_lines = lines[start_idx:end_idx]
        elif start_idx is not None:
            content_lines = lines[start_idx:]
        elif end_idx is not None:
            # No clear start, use heuristic
            actual_start = self._find_actual_start(lines[:end_idx])
            content_lines = lines[actual_start:end_idx]
        else:
            # No markers found, use heuristics
            actual_start = self._find_actual_start(lines)
            actual_end = self._find_actual_end(lines)
            content_lines = lines[actual_start:actual_end]
        
        # Clean content
        content_lines = self._clean_lines(content_lines)
        content = '\n'.join(content_lines)
        
        # If no title found, try to extract from content
        if not metadata.title:
            metadata.title = self._extract_title_from_content(content_lines[:100])
        
        return content, metadata
    
    def _find_start(self, lines: List[str]) -> Optional[int]:
        """Find start of actual content using line-based checks."""
        for i, line in enumerate(lines[:1000]):
            line_upper = line.upper()
            
            # Most common Gutenberg start marker
            if 'START OF' in line_upper and 'PROJECT GUTENBERG' in line_upper:
                # Skip blank lines after marker
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                return j
            
            # Older format
            if 'END*THE SMALL PRINT' in line or 'END THE SMALL PRINT' in line_upper:
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                return j
            
            # Sometimes marked with asterisks
            if line.strip() == '***' and i > 10:  # Not at very beginning
                # Check if next non-blank line looks like start
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines):
                    next_line = lines[j].strip()
                    # If it looks like a title or chapter, this might be the start
                    if (next_line and 
                        (next_line[0].isupper() or 
                         any(word in next_line.upper() for word in ['CHAPTER', 'PART', 'BOOK']))):
                        return j
        
        return None
    
    def _find_end(self, lines: List[str]) -> Optional[int]:
        """Find end of actual content using line-based checks."""
        # Search from the end backwards
        for i in range(len(lines) - 1, max(len(lines) - 1000, 0), -1):
            line_upper = lines[i].upper()
            
            # Most common end marker
            if 'END OF' in line_upper and 'PROJECT GUTENBERG' in line_upper:
                # Back up over blank lines
                j = i - 1
                while j > 0 and not lines[j].strip():
                    j -= 1
                return j + 1
            
            # Other end markers
            if lines[i].startswith('End of the Project Gutenberg'):
                return i
            
            if lines[i].startswith('End of Project Gutenberg'):
                return i
            
            if '***** This file should be named' in lines[i]:
                return i
            
            # Simple "THE END" marker
            if lines[i].strip().upper() == 'THE END':
                return i + 1
        
        return None
    
    def _find_actual_start(self, lines: List[str]) -> int:
        """
        Find actual content start when no markers found.
        
        Looks for first substantial text or chapter marker.
        """
        consecutive_short = 0
        
        for i, line in enumerate(lines[:500]):
            line_stripped = line.strip()
            
            # Common chapter/section markers
            for marker in ['CHAPTER', 'Chapter', 'PART', 'Part', 'ACT', 'Act', 'BOOK', 'Book', 'PROLOGUE', 'Prologue']:
                if line_stripped.startswith(marker + ' '):
                    return i
            
            # Skip short lines at beginning (likely metadata)
            if len(line_stripped) < 50:
                consecutive_short += 1
            else:
                # Found substantial text
                if consecutive_short > 5:
                    # We skipped past header stuff
                    return i
                consecutive_short = 0
        
        return 0
    
    def _find_actual_end(self, lines: List[str]) -> int:
        """Find actual content end when no markers found."""
        # Look for common end phrases
        end_phrases = [
            'produced by', 'end of', 'transcriber', 'ebook', 
            'gutenberg', 'finis', 'the end', 'updated editions',
            'distributed proofreading', 'ascii', 'encoding'
        ]
        
        for i in range(len(lines) - 1, max(len(lines) - 500, 0), -1):
            line_lower = lines[i].lower()
            
            for phrase in end_phrases:
                if phrase in line_lower:
                    return i
        
        return len(lines)
    
    def _extract_metadata(self, header_lines: List[str]) -> GutenbergMetadata:
        """Extract metadata from header lines using simple string operations."""
        metadata = GutenbergMetadata()
        
        for line in header_lines:
            line_stripped = line.strip()
            
            # Title
            if line_stripped.startswith('Title:'):
                metadata.title = line_stripped[6:].strip()
            elif 'EBook of' in line and not metadata.title:
                # Extract from "Project Gutenberg EBook of X"
                parts = line.split('EBook of')
                if len(parts) > 1:
                    title_part = parts[1]
                    # Remove "by" clause if present
                    if ' by ' in title_part:
                        title_part = title_part.split(' by ')[0]
                    metadata.title = title_part.strip().strip(',')
            
            # Author
            if line_stripped.startswith('Author:'):
                metadata.author = line_stripped[7:].strip()
            elif line_stripped.lower().startswith('by ') and not metadata.author:
                # Line starts with "by Author Name"
                metadata.author = line_stripped[3:].strip()
            
            # Language
            if line_stripped.startswith('Language:'):
                metadata.language = line_stripped[9:].strip()
            
            # Release date
            if line_stripped.startswith('Release Date:'):
                metadata.release_date = line_stripped[13:].strip()
            elif line_stripped.startswith('Posting Date:'):
                metadata.posting_date = line_stripped[13:].strip()
            
            # Last updated
            if line_stripped.startswith('Last Updated:'):
                metadata.last_updated = line_stripped[13:].strip()
            
            # Producer
            if line_stripped.startswith('Produced by'):
                metadata.produced_by = line_stripped[11:].strip()
            
            # EBook number (look for [EBook #12345] pattern)
            if 'EBook #' in line and not metadata.ebook_number:
                parts = line.split('EBook #')
                if len(parts) > 1:
                    # Extract number
                    num_part = parts[1]
                    num = ''
                    for char in num_part:
                        if char.isdigit():
                            num += char
                        elif num:  # Stop at first non-digit after we have digits
                            break
                    if num:
                        metadata.ebook_number = num
        
        return metadata
    
    def _extract_title_from_content(self, lines: List[str]) -> Optional[str]:
        """
        Try to extract title from the beginning of content.
        
        Often the title appears as the first non-blank line.
        """
        for line in lines:
            line_stripped = line.strip()
            
            # Skip blank lines
            if not line_stripped:
                continue
            
            # Skip if it's a chapter/part marker
            skip_markers = ['CHAPTER', 'Chapter', 'PART', 'Part', 'ACT', 'Act', 'BOOK', 'Book']
            if any(line_stripped.startswith(marker) for marker in skip_markers):
                continue
            
            # Skip if too short or too long to be a title
            if len(line_stripped) < 3 or len(line_stripped) > 100:
                continue
            
            # Skip lines that look like metadata
            if ':' in line_stripped[:20]:  # Colon near beginning suggests "Field: Value"
                continue
            
            # This might be the title
            if line_stripped.isupper():
                # Convert from all caps
                return line_stripped.title()
            elif line_stripped[0].isupper():
                # Already in good format
                return line_stripped.rstrip('.,;:')
        
        return None
    
    def _clean_lines(self, lines: List[str]) -> List[str]:
        """
        Clean content lines.
        
        Removes:
        - Multiple consecutive blank lines (keep max 2)
        - Page numbers (lines with just numbers)
        - Illustration markers
        """
        cleaned = []
        blank_count = 0
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip page numbers (just digits possibly with spaces)
            if line_stripped and all(c.isdigit() or c.isspace() for c in line_stripped):
                continue
            
            # Skip illustration markers
            if line_stripped.startswith('[Illustration'):
                continue
            
            # Handle blank lines (keep max 2 consecutive)
            if not line_stripped:
                blank_count += 1
                if blank_count <= 2:
                    cleaned.append(line)
            else:
                blank_count = 0
                cleaned.append(line)
        
        return cleaned
    
    def get_toc(self, text: str) -> Optional[str]:
        """
        Extract table of contents if present.
        
        Returns the TOC section as a string, or None if not found.
        """
        lines = text.split('\n')
        toc_start = -1
        toc_end = -1
        
        # Look for TOC markers
        for i, line in enumerate(lines[:500]):  # TOC usually in first 500 lines
            line_lower = line.lower().strip()
            
            # TOC markers
            if line_lower in ['contents', 'table of contents', 'contents.', 'table of contents.']:
                toc_start = i
                break
            
            # Sometimes just "CONTENTS" in caps
            if line.strip() == 'CONTENTS':
                toc_start = i
                break
        
        if toc_start == -1:
            return None
        
        # Find TOC end (many blank lines or chapter start)
        consecutive_blanks = 0
        chapter_markers = ['CHAPTER', 'Chapter', 'PART', 'Part', 'ACT', 'Act', 
                          'BOOK', 'Book', 'PROLOGUE', 'Prologue', 'INTRODUCTION', 'Introduction']
        
        for i in range(toc_start + 1, min(toc_start + 200, len(lines))):
            line_stripped = lines[i].strip()
            
            if not line_stripped:
                consecutive_blanks += 1
                if consecutive_blanks > 3:
                    toc_end = i
                    break
            else:
                consecutive_blanks = 0
                # Check for chapter start
                for marker in chapter_markers:
                    if line_stripped.startswith(marker + ' ') or line_stripped.startswith(marker + '.'):
                        toc_end = i
                        break
                if toc_end != -1:
                    break
        
        if toc_end == -1:
            toc_end = min(toc_start + 100, len(lines))
        
        return '\n'.join(lines[toc_start:toc_end])


# Convenience function for backward compatibility
def clean_gutenberg_text(text: str) -> Tuple[str, GutenbergMetadata]:
    """
    Clean Project Gutenberg text.
    
    Args:
        text: Raw Gutenberg text
        
    Returns:
        Tuple of (cleaned_text, metadata)
    """
    parser = GutenbergParser()
    return parser.clean(text)