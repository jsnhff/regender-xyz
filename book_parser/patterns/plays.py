"""Play and drama pattern definitions"""

from .base import Pattern, PatternType, NumberType


# Roman numeral pattern component
ROMAN = r'[IVXLCDM]+'


PLAY_PATTERNS = [
    # Act patterns
    Pattern(
        regex=r'^ACT\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.ACT,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=130,
        description="ACT I"
    ),
    Pattern(
        regex=r'^Act\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.ACT,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=130,
        description="Act I"
    ),
    Pattern(
        regex=r'^ACT\s+(\d+)\.?\s*$',
        pattern_type=PatternType.ACT,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=130,
        description="ACT 1"
    ),
    Pattern(
        regex=r'^Act\s+(\d+)\.?\s*$',
        pattern_type=PatternType.ACT,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=130,
        description="Act 1"
    ),
    
    # Scene patterns with location
    Pattern(
        regex=r'^SCENE\s+(' + ROMAN + r')\.\s*(.+)$',
        pattern_type=PatternType.SCENE,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number', 2: 'title'},
        priority=125,
        description="SCENE I. Location"
    ),
    Pattern(
        regex=r'^Scene\s+(' + ROMAN + r')\.\s*(.+)$',
        pattern_type=PatternType.SCENE,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number', 2: 'title'},
        priority=125,
        description="Scene I. Location"
    ),
    Pattern(
        regex=r'^SCENE\s+(\d+)\.\s*(.+)$',
        pattern_type=PatternType.SCENE,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number', 2: 'title'},
        priority=125,
        description="SCENE 1. Location"
    ),
    Pattern(
        regex=r'^Scene\s+(\d+)\.\s*(.+)$',
        pattern_type=PatternType.SCENE,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number', 2: 'title'},
        priority=125,
        description="Scene 1. Location"
    ),
    
    # Scene patterns without location
    Pattern(
        regex=r'^SCENE\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.SCENE,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=120,
        description="SCENE I"
    ),
    Pattern(
        regex=r'^Scene\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.SCENE,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=120,
        description="Scene I"
    ),
    Pattern(
        regex=r'^SCENE\s+(\d+)\.?\s*$',
        pattern_type=PatternType.SCENE,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=120,
        description="SCENE 1"
    ),
    Pattern(
        regex=r'^Scene\s+(\d+)\.?\s*$',
        pattern_type=PatternType.SCENE,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=120,
        description="Scene 1"
    ),
    
    # Multi-line patterns (for future implementation)
    # These are placeholders showing how we'll handle ACT/SCENE on different lines
    Pattern(
        regex=r'^ACT\s+(' + ROMAN + r')\s*$',
        pattern_type=PatternType.ACT,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=130,
        description="ACT I (multi-line)",
        multiline=True,
        follow_pattern=r'^Scene\s+([ivxlcdm]+|\\d+)\\.\\s*(.*)$'
    ),
]