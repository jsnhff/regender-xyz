"""
Multi-Level Hierarchy Builder

Handles complex book structures with nested sections.
"""

import re
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum


class SectionType(Enum):
    """Types of book sections."""
    VOLUME = "volume"
    PART = "part"
    BOOK = "book"
    ACT = "act"
    CHAPTER = "chapter"
    SCENE = "scene"
    LETTER = "letter"
    POEM = "poem"
    SECTION = "section"
    PARAGRAPH = "paragraph"


@dataclass
class Section:
    """A section of a book."""
    type: SectionType
    number: Optional[str] = None  # Could be "1", "I", "One", etc.
    title: Optional[str] = None
    content: List[str] = field(default_factory=list)  # Lines of text
    subsections: List['Section'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_line(self, line: str):
        """Add a line to this section's content."""
        self.content.append(line)
    
    def add_subsection(self, subsection: 'Section'):
        """Add a subsection."""
        self.subsections.append(subsection)
    
    def get_full_title(self) -> str:
        """Get the full title including number."""
        if self.number and self.title:
            return f"{self.type.value.title()} {self.number}: {self.title}"
        elif self.number:
            return f"{self.type.value.title()} {self.number}"
        elif self.title:
            return self.title
        else:
            return self.type.value.title()
    
    def to_flat_chapters(self) -> List[Dict[str, Any]]:
        """
        Convert hierarchical structure to flat list of chapters.
        This is for compatibility with the existing JSON format.
        """
        chapters = []
        
        if self.subsections:
            # This section has subsections
            for subsection in self.subsections:
                if subsection.subsections:
                    # Recursive case
                    chapters.extend(subsection.to_flat_chapters())
                else:
                    # Leaf node - this is an actual chapter
                    chapter = {
                        'title': subsection.get_full_title(),
                        'number': subsection.number,
                        'paragraphs': subsection.content,
                        'type': subsection.type.value
                    }
                    # Add parent info for context
                    if self.type != SectionType.BOOK:
                        chapter['parent'] = self.get_full_title()
                    chapters.append(chapter)
        else:
            # This is a leaf section (actual content)
            chapter = {
                'title': self.get_full_title(),
                'number': self.number,
                'paragraphs': self.content,
                'type': self.type.value
            }
            chapters.append(chapter)
        
        return chapters


class HierarchyBuilder:
    """
    Builds hierarchical structure from parsed text.
    """
    
    def __init__(self):
        """Initialize the hierarchy builder."""
        self._setup_patterns()
    
    def _setup_patterns(self):
        """Set up section detection patterns."""
        # Patterns for different section types
        self.patterns = {
            SectionType.VOLUME: [
                (r'^\s*VOLUME\s+([IVX]+)', lambda m: m.group(1)),
                (r'^\s*Volume\s+([IVX]+)', lambda m: m.group(1)),
                (r'^\s*VOLUME\s+(ONE|TWO|THREE|FOUR|FIVE)', lambda m: m.group(1)),
                (r'^\s*Vol\.\s*(\d+)', lambda m: m.group(1)),
            ],
            SectionType.PART: [
                (r'^\s*PART\s+([IVX]+)', lambda m: m.group(1)),
                (r'^\s*Part\s+([IVX]+)', lambda m: m.group(1)),
                (r'^\s*PART\s+(ONE|TWO|THREE|FOUR|FIVE)', lambda m: m.group(1)),
            ],
            SectionType.BOOK: [
                (r'^\s*BOOK\s+([IVX]+)', lambda m: m.group(1)),
                (r'^\s*Book\s+([IVX]+)', lambda m: m.group(1)),
                (r'^\s*BOOK\s+(ONE|TWO|THREE|FOUR|FIVE)', lambda m: m.group(1)),
            ],
            SectionType.ACT: [
                (r'^\s*ACT\s+([IVX]+)', lambda m: m.group(1)),
                (r'^\s*Act\s+([IVX]+)', lambda m: m.group(1)),
                (r'^\s*ACTUS\s+([IVX]+)', lambda m: m.group(1)),  # Latin
            ],
            SectionType.CHAPTER: [
                (r'^\s*CHAPTER\s+([IVX]+)\.?\s*(.*)', lambda m: (m.group(1), m.group(2).strip())),
                (r'^\s*Chapter\s+([IVX]+)\.?\s*(.*)', lambda m: (m.group(1), m.group(2).strip())),
                (r'^\s*CHAPTER\s+(\d+)\.?\s*(.*)', lambda m: (m.group(1), m.group(2).strip())),
                (r'^\s*Chapter\s+(\d+)\.?\s*(.*)', lambda m: (m.group(1), m.group(2).strip())),
                (r'^\s*([IVX]+)\.\s+([A-Z][A-Z ]+)$', lambda m: (m.group(1), m.group(2).strip())),  # Roman + CAPS title
                (r'^\s*([IVX]+)\.\s+([A-Z].+)', lambda m: (m.group(1), m.group(2).strip())),  # Roman + title
                (r'^\s*([IVX]+)\.?\s*$', lambda m: m.group(1)),  # Just Roman numerals
                (r'^\s*(\d+)\.\s+(.+)', lambda m: (m.group(1), m.group(2).strip())),
                (r'^\s*ADVENTURE\s+([IVX]+)', lambda m: m.group(1)),  # Adventure stories
                (r'^\s*Story\s+([IVX]+)', lambda m: m.group(1)),  # Story format
            ],
            SectionType.SCENE: [
                (r'^\s*SCENE\s+([ivxIVX]+)', lambda m: m.group(1)),
                (r'^\s*Scene\s+([ivxIVX]+)', lambda m: m.group(1)),
                (r'^\s*Sc\.\s*([ivxIVX]+)', lambda m: m.group(1)),
            ],
            SectionType.LETTER: [
                (r'^\s*LETTER\s+([IVX]+)', lambda m: m.group(1)),
                (r'^\s*Letter\s+([IVX]+)', lambda m: m.group(1)),
                (r'^\s*LETTER\s+(\d+)', lambda m: m.group(1)),
            ],
            SectionType.POEM: [
                (r'^\s*(\d+)\s*$', lambda m: m.group(1)),
                (r'^\s*([IVX]+)\s*$', lambda m: m.group(1)),
                (r'^\s*Sonnet\s+(\d+)', lambda m: m.group(1)),
            ],
        }
    
    def build_hierarchy(self, lines: List[str], format_hint: str = None, skip_toc: bool = True) -> Section:
        """
        Build hierarchical structure from lines of text.
        
        Args:
            lines: Lines of text
            format_hint: Hint about the format (e.g., "multi_part", "play")
            skip_toc: Whether to skip table of contents at beginning
            
        Returns:
            Root Section containing the hierarchy
        """
        # Create root section
        root = Section(type=SectionType.BOOK, title="Book")
        
        # Determine hierarchy levels based on format
        if format_hint == "multi_part":
            hierarchy = [SectionType.VOLUME, SectionType.CHAPTER]
        elif format_hint == "play":
            hierarchy = [SectionType.ACT, SectionType.SCENE]
        else:
            # Auto-detect hierarchy
            hierarchy = self._detect_hierarchy(lines)
        
        # Skip TOC if needed
        start_index = 0
        if skip_toc:
            start_index = self._find_content_start(lines, hierarchy)
        
        # Build the structure
        current_sections = {level: None for level in hierarchy}
        current_sections[SectionType.BOOK] = root
        
        for i in range(start_index, len(lines)):
            line = lines[i]
            line_stripped = line.strip()
            if not line_stripped:
                # Add blank lines to current content
                lowest_section = self._get_lowest_section(current_sections)
                if lowest_section:
                    lowest_section.add_line(line)
                continue
            
            # Check if this line starts a new section
            section_match = self._match_section(line_stripped)
            
            if section_match:
                section_type, number, title = section_match
                
                # Create new section
                new_section = Section(
                    type=section_type,
                    number=number,
                    title=title
                )
                
                # Find parent section
                parent = self._find_parent_section(section_type, current_sections, hierarchy)
                if parent:
                    parent.add_subsection(new_section)
                    current_sections[section_type] = new_section
                    
                    # Clear lower-level sections
                    self._clear_lower_sections(section_type, current_sections, hierarchy)
            else:
                # Add line to current lowest section
                lowest_section = self._get_lowest_section(current_sections)
                if lowest_section:
                    lowest_section.add_line(line)
                else:
                    root.add_line(line)
        
        return root
    
    def _detect_hierarchy(self, lines: List[str]) -> List[SectionType]:
        """
        Auto-detect the hierarchy levels in the text.
        """
        found_types = set()
        
        # Sample first 1000 lines
        for line in lines[:1000]:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            for section_type, patterns in self.patterns.items():
                for pattern, _ in patterns:
                    if re.match(pattern, line_stripped):
                        found_types.add(section_type)
                        break
        
        # Determine hierarchy based on what was found
        if SectionType.VOLUME in found_types:
            if SectionType.CHAPTER in found_types:
                return [SectionType.VOLUME, SectionType.CHAPTER]
            elif SectionType.BOOK in found_types:
                return [SectionType.VOLUME, SectionType.BOOK, SectionType.CHAPTER]
        elif SectionType.PART in found_types:
            if SectionType.CHAPTER in found_types:
                return [SectionType.PART, SectionType.CHAPTER]
        elif SectionType.ACT in found_types:
            if SectionType.SCENE in found_types:
                return [SectionType.ACT, SectionType.SCENE]
            else:
                return [SectionType.ACT]
        elif SectionType.CHAPTER in found_types:
            return [SectionType.CHAPTER]
        elif SectionType.LETTER in found_types:
            return [SectionType.LETTER]
        elif SectionType.POEM in found_types:
            return [SectionType.POEM]
        
        # Default to chapters
        return [SectionType.CHAPTER]
    
    def _match_section(self, line: str) -> Optional[tuple]:
        """
        Check if a line matches any section pattern.
        
        Returns:
            Tuple of (section_type, number, title) or None
        """
        for section_type, patterns in self.patterns.items():
            for pattern, extractor in patterns:
                match = re.match(pattern, line)
                if match:
                    result = extractor(match)
                    if isinstance(result, tuple):
                        number, title = result
                    else:
                        number = result
                        title = None
                    return (section_type, number, title)
        return None
    
    def _find_parent_section(self, section_type: SectionType, 
                            current_sections: Dict[SectionType, Section],
                            hierarchy: List[SectionType]) -> Optional[Section]:
        """
        Find the appropriate parent for a new section.
        """
        if section_type not in hierarchy:
            return current_sections.get(SectionType.BOOK)
        
        type_index = hierarchy.index(section_type)
        
        # Look for parent in hierarchy
        if type_index > 0:
            parent_type = hierarchy[type_index - 1]
            parent = current_sections.get(parent_type)
            if parent:
                return parent
        
        # Fall back to root
        return current_sections.get(SectionType.BOOK)
    
    def _get_lowest_section(self, current_sections: Dict[SectionType, Section]) -> Optional[Section]:
        """
        Get the lowest level section that's currently active.
        """
        # Priority order (lowest to highest)
        priority = [
            SectionType.SCENE, SectionType.CHAPTER, SectionType.LETTER,
            SectionType.POEM, SectionType.ACT, SectionType.BOOK,
            SectionType.PART, SectionType.VOLUME
        ]
        
        for section_type in priority:
            if section_type in current_sections and current_sections[section_type]:
                return current_sections[section_type]
        
        return None
    
    def _clear_lower_sections(self, section_type: SectionType,
                              current_sections: Dict[SectionType, Section],
                              hierarchy: List[SectionType]):
        """
        Clear sections lower in the hierarchy.
        """
        if section_type not in hierarchy:
            return
        
        type_index = hierarchy.index(section_type)
        
        # Clear all sections lower in hierarchy
        for i in range(type_index + 1, len(hierarchy)):
            lower_type = hierarchy[i]
            if lower_type in current_sections:
                current_sections[lower_type] = None
    
    def _find_content_start(self, lines: List[str], hierarchy: List[SectionType]) -> int:
        """
        Find where actual content starts (after TOC).
        
        Simple approach: Look for contents/table of contents marker,
        then find the first section marker that appears twice
        (once in TOC, once in actual content).
        """
        toc_found = False
        toc_line = -1
        
        # Look for explicit TOC markers
        for i in range(min(100, len(lines))):
            line_lower = lines[i].lower().strip()
            if 'contents' in line_lower and len(line_lower) < 50:
                toc_found = True
                toc_line = i
                break
        
        if not toc_found:
            return 0  # No TOC, start from beginning
        
        # Now collect all section markers after TOC line
        seen_sections = {}
        
        for i in range(toc_line, min(len(lines), 2000)):
            line = lines[i].strip()
            if not line:
                continue
                
            match = self._match_section(line)
            if match:
                section_type, number, title = match
                # Create a key for this section
                if section_type == SectionType.CHAPTER and number:
                    key = f"chapter_{number}"
                elif section_type == SectionType.VOLUME and number:
                    key = f"volume_{number}"
                elif section_type == SectionType.PART and number:
                    key = f"part_{number}"
                else:
                    continue
                
                if key in seen_sections:
                    # We've seen this before - this is likely the real content
                    # But for volumes/parts, return the line itself
                    # For chapters, we might need to go back to find the volume
                    if section_type in [SectionType.VOLUME, SectionType.PART, SectionType.BOOK]:
                        return i
                    else:
                        # Look back for a volume/part marker
                        for j in range(i-1, max(i-50, toc_line), -1):
                            back_match = self._match_section(lines[j].strip())
                            if back_match and back_match[0] in [SectionType.VOLUME, SectionType.PART]:
                                return j
                        return i
                else:
                    seen_sections[key] = i
        
        return 0  # No duplicate found, no TOC