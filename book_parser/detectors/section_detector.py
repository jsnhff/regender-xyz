"""Section detection logic"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re

from ..patterns import PatternRegistry, PatternType


@dataclass
class DetectedSection:
    """A detected section in the book"""
    pattern_type: PatternType
    start_line: int
    end_line: Optional[int] = None
    number: Optional[str] = None
    title: Optional[str] = None
    content_lines: List[str] = None
    metadata: Dict[str, str] = None
    
    def __post_init__(self):
        if self.content_lines is None:
            self.content_lines = []
        if self.metadata is None:
            self.metadata = {}


class SectionDetector:
    """Detects sections in book text"""
    
    def __init__(self, pattern_registry: PatternRegistry):
        self.pattern_registry = pattern_registry
        
        # Special section patterns
        self.special_sections = {
            'epilogue': re.compile(r'\bEPILOGUE\b', re.IGNORECASE),
            'appendix': re.compile(r'\bAPPENDI[XC]\b', re.IGNORECASE),
            'etymology': re.compile(r'\bETYMOLOGY\b', re.IGNORECASE),
            'extracts': re.compile(r'\bEXTRACTS\b', re.IGNORECASE),
            'prologue': re.compile(r'\bPROLOGUE\b', re.IGNORECASE),
        }
        
        # TOC patterns
        self.toc_patterns = [
            re.compile(r'^\s*CONTENTS?\s*$', re.IGNORECASE),
            re.compile(r'^\s*TABLE\s+OF\s+CONTENTS?\s*$', re.IGNORECASE),
        ]
        
        # End of book patterns
        self.end_patterns = [
            re.compile(r'^\s*THE\s+END\s*$', re.IGNORECASE),
            re.compile(r'^\s*FINIS\s*$', re.IGNORECASE),
            re.compile(r'^\s*FIN\s*$', re.IGNORECASE),
        ]
    
    def detect_sections(self, lines: List[str], 
                       detect_frontmatter: bool = True,
                       min_section_lines: int = 5,
                       min_priority_threshold: int = 10) -> List[DetectedSection]:
        """
        Detect all sections in the book
        
        Args:
            lines: Lines of text
            detect_frontmatter: Whether to detect frontmatter
            min_section_lines: Minimum lines for a valid section
            min_priority_threshold: Minimum priority for patterns in first pass
            
        Returns:
            List of detected sections
        """
        sections = []
        current_section = None
        
        # First pass: try with higher priority patterns only
        sections = self._detect_with_priority(lines, detect_frontmatter, 
                                            min_section_lines, min_priority_threshold)
        
        # If we found reasonable sections, return them
        content_sections = [s for s in sections if s.pattern_type not in [
            PatternType.FRONTMATTER, PatternType.TOC
        ]]
        if len(content_sections) >= 3:  # Found at least 3 content sections
            return sections
        
        # Second pass: try with all patterns if first pass didn't find enough
        if min_priority_threshold > 0:
            sections = self._detect_with_priority(lines, detect_frontmatter, 
                                                min_section_lines, 0)
        
        return sections
    
    def _detect_with_priority(self, lines: List[str], 
                             detect_frontmatter: bool,
                             min_section_lines: int,
                             min_priority: int) -> List[DetectedSection]:
        """Internal method to detect sections with priority threshold"""
        sections = []
        current_section = None
        
        # Detect frontmatter if requested
        if detect_frontmatter:
            frontmatter_end = self._find_first_content_section(lines)
            if frontmatter_end > 0:
                sections.append(DetectedSection(
                    pattern_type=PatternType.FRONTMATTER,
                    start_line=0,
                    end_line=frontmatter_end,
                    content_lines=lines[:frontmatter_end]
                ))
        
        # Process lines
        for i, line in enumerate(lines):
            # Skip if we're still in frontmatter
            if sections and sections[-1].pattern_type == PatternType.FRONTMATTER and i < sections[-1].end_line:
                continue
            
            # Check for special sections
            special_type = self._check_special_section(line)
            if special_type:
                if current_section:
                    current_section.end_line = i
                    if len(current_section.content_lines) >= min_section_lines:
                        sections.append(current_section)
                
                current_section = DetectedSection(
                    pattern_type=special_type,
                    start_line=i,
                    title=line.strip()
                )
                continue
            
            # Check for TOC
            if self._is_toc_header(line):
                if current_section:
                    current_section.end_line = i
                    if len(current_section.content_lines) >= min_section_lines:
                        sections.append(current_section)
                
                # Find TOC end
                toc_end = self._find_toc_end(lines, i + 1)
                sections.append(DetectedSection(
                    pattern_type=PatternType.TOC,
                    start_line=i,
                    end_line=toc_end,
                    content_lines=lines[i:toc_end]
                ))
                current_section = None
                continue
            
            # Check for regular sections (chapters, acts, etc.)
            match_result = self.pattern_registry.match_line(line)
            if match_result:
                pattern, match, info = match_result
                
                # Skip patterns below priority threshold
                if pattern.priority < min_priority:
                    if current_section:
                        current_section.content_lines.append(line)
                    continue
                
                # Handle multi-line patterns
                if pattern.multiline and pattern.follow_pattern and i + 1 < len(lines):
                    follow_match = re.match(pattern.follow_pattern, lines[i + 1].strip())
                    if not follow_match:
                        # Not a valid multi-line match, treat as content
                        if current_section:
                            current_section.content_lines.append(line)
                        continue
                
                # Close previous section
                if current_section:
                    current_section.end_line = i
                    if len(current_section.content_lines) >= min_section_lines:
                        sections.append(current_section)
                
                # Start new section
                current_section = DetectedSection(
                    pattern_type=pattern.pattern_type,
                    start_line=i,
                    number=info.get('number'),
                    title=info.get('title'),
                    metadata=info
                )
                continue
            
            # Check for end of book
            if self._is_end_of_book(line):
                if current_section:
                    current_section.end_line = i
                    if len(current_section.content_lines) >= min_section_lines:
                        sections.append(current_section)
                    current_section = None
                break
            
            # Add line to current section
            if current_section:
                current_section.content_lines.append(line)
        
        # Close final section
        if current_section:
            current_section.end_line = len(lines)
            if len(current_section.content_lines) >= min_section_lines:
                sections.append(current_section)
        
        return sections
    
    def _find_first_content_section(self, lines: List[str]) -> int:
        """Find where actual content begins"""
        for i, line in enumerate(lines):
            # Check if this is a content section
            match_result = self.pattern_registry.match_line(line)
            if match_result:
                pattern, _, _ = match_result
                if pattern.pattern_type in [PatternType.CHAPTER, PatternType.ACT, 
                                          PatternType.PART, PatternType.LIVRE]:
                    return i
            
            # Check for special sections that mark content start
            if self._check_special_section(line) in [PatternType.PROLOGUE, PatternType.ETYMOLOGY]:
                return i
        
        return 0
    
    def _check_special_section(self, line: str) -> Optional[PatternType]:
        """Check if line is a special section header"""
        for section_name, pattern in self.special_sections.items():
            if pattern.search(line):
                return PatternType(section_name)
        return None
    
    def _is_toc_header(self, line: str) -> bool:
        """Check if line is a table of contents header"""
        return any(pattern.match(line) for pattern in self.toc_patterns)
    
    def _find_toc_end(self, lines: List[str], start_idx: int) -> int:
        """Find where TOC ends"""
        # Simple heuristic: TOC ends when we find a chapter or empty lines followed by chapter
        empty_count = 0
        for i in range(start_idx, len(lines)):
            line = lines[i].strip()
            
            if not line:
                empty_count += 1
                if empty_count > 3:  # Multiple empty lines might signal end
                    return i
            else:
                empty_count = 0
                
                # Check if this is a chapter start
                match_result = self.pattern_registry.match_line(line)
                if match_result:
                    pattern, _, _ = match_result
                    if pattern.pattern_type in [PatternType.CHAPTER, PatternType.PART, 
                                              PatternType.ACT, PatternType.PROLOGUE]:
                        return i
        
        return min(start_idx + 50, len(lines))  # Default: max 50 lines for TOC
    
    def _is_end_of_book(self, line: str) -> bool:
        """Check if line indicates end of book"""
        return any(pattern.match(line) for pattern in self.end_patterns)