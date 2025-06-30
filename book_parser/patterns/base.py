"""Base pattern definitions and types"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import re


class PatternType(Enum):
    """Types of patterns we can match"""
    CHAPTER = "chapter"
    PART = "part"
    BOOK = "book"
    ACT = "act"
    SCENE = "scene"
    LETTER = "letter"
    ENTRY = "entry"
    STORY = "story"
    SECTION = "section"
    EPILOGUE = "epilogue"
    PROLOGUE = "prologue"
    APPENDIX = "appendix"
    FRONTMATTER = "frontmatter"
    TOC = "toc"
    LIVRE = "livre"  # French book divisions
    ETYMOLOGY = "etymology"
    EXTRACTS = "extracts"
    UNKNOWN = "unknown"


class NumberType(Enum):
    """Types of numbering systems"""
    ARABIC = "arabic"       # 1, 2, 3
    ROMAN = "roman"         # I, II, III
    WORD = "word"          # One, Two, Three
    ORDINAL = "ordinal"    # First, Second, Third
    NONE = "none"          # No numbering


@dataclass
class Pattern:
    """A single pattern definition"""
    regex: str
    pattern_type: PatternType
    number_type: NumberType
    language: str = "english"
    priority: int = 100
    capture_groups: Dict[int, str] = None
    description: str = ""
    multiline: bool = False
    follow_pattern: Optional[str] = None
    
    def __post_init__(self):
        if self.capture_groups is None:
            self.capture_groups = {}
        self.compiled = re.compile(self.regex, re.IGNORECASE if self.language == "english" else 0)
    
    def match(self, line: str) -> Optional[re.Match]:
        """Match this pattern against a line"""
        return self.compiled.match(line.strip())
    
    def extract_info(self, match: re.Match) -> Dict[str, str]:
        """Extract information from a match"""
        info = {
            "type": self.pattern_type.value,
            "number_type": self.number_type.value
        }
        
        for group_num, group_name in self.capture_groups.items():
            if group_num <= len(match.groups()):
                info[group_name] = match.group(group_num)
        
        return info