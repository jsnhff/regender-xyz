"""Pattern registry for managing and matching patterns"""

from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import re

from .base import Pattern, PatternType
from .standard import ENGLISH_PATTERNS
from .international import INTERNATIONAL_PATTERNS
from .plays import PLAY_PATTERNS


class PatternRegistry:
    """Registry for managing book parsing patterns"""
    
    def __init__(self):
        self.patterns: List[Pattern] = []
        self.patterns_by_type: Dict[PatternType, List[Pattern]] = defaultdict(list)
        self.patterns_by_language: Dict[str, List[Pattern]] = defaultdict(list)
        
        # Load default patterns
        self._load_default_patterns()
    
    def _load_default_patterns(self):
        """Load all default patterns"""
        self.register_patterns(ENGLISH_PATTERNS)
        self.register_patterns(INTERNATIONAL_PATTERNS)
        self.register_patterns(PLAY_PATTERNS)
    
    def register_pattern(self, pattern: Pattern):
        """Register a single pattern"""
        self.patterns.append(pattern)
        self.patterns_by_type[pattern.pattern_type].append(pattern)
        self.patterns_by_language[pattern.language].append(pattern)
        
        # Sort by priority (highest first)
        self.patterns.sort(key=lambda p: p.priority, reverse=True)
    
    def register_patterns(self, patterns: List[Pattern]):
        """Register multiple patterns"""
        for pattern in patterns:
            self.register_pattern(pattern)
    
    def match_line(self, line: str, 
                   pattern_types: Optional[List[PatternType]] = None,
                   languages: Optional[List[str]] = None) -> Optional[Tuple[Pattern, re.Match, Dict[str, str]]]:
        """
        Match a line against registered patterns
        
        Args:
            line: Line to match
            pattern_types: Optional list of pattern types to consider
            languages: Optional list of languages to consider
            
        Returns:
            Tuple of (pattern, match, extracted_info) or None
        """
        # Get candidate patterns
        if pattern_types:
            candidates = []
            for ptype in pattern_types:
                candidates.extend(self.patterns_by_type[ptype])
            # Remove duplicates while preserving order
            seen = set()
            candidates = [p for p in candidates if not (p in seen or seen.add(p))]
        elif languages:
            candidates = []
            for lang in languages:
                candidates.extend(self.patterns_by_language[lang])
            # Remove duplicates while preserving order
            seen = set()
            candidates = [p for p in candidates if not (p in seen or seen.add(p))]
        else:
            candidates = self.patterns
        
        # Sort by priority if we filtered
        if pattern_types or languages:
            candidates.sort(key=lambda p: p.priority, reverse=True)
        
        # Try patterns in priority order
        for pattern in candidates:
            match = pattern.match(line)
            if match:
                info = pattern.extract_info(match)
                return pattern, match, info
        
        return None
    
    def get_patterns_by_type(self, pattern_type: PatternType) -> List[Pattern]:
        """Get all patterns of a specific type"""
        return self.patterns_by_type[pattern_type].copy()
    
    def get_patterns_by_language(self, language: str) -> List[Pattern]:
        """Get all patterns for a specific language"""
        return self.patterns_by_language[language].copy()
    
    def clear_patterns(self):
        """Clear all registered patterns"""
        self.patterns.clear()
        self.patterns_by_type.clear()
        self.patterns_by_language.clear()
    
    def get_pattern_count(self) -> int:
        """Get total number of registered patterns"""
        return len(self.patterns)
    
    def get_pattern_summary(self) -> Dict[str, int]:
        """Get summary of patterns by type"""
        summary = {}
        for ptype, patterns in self.patterns_by_type.items():
            summary[ptype.value] = len(patterns)
        return summary