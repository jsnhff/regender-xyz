"""International language pattern definitions"""

from .base import Pattern, PatternType, NumberType


# Roman numeral pattern component
ROMAN = r'[IVXLCDM]+'

# French number words
FRENCH_NUMBER_WORDS = r'(?:premier|deuxième|troisième|quatrième|cinquième|' \
                      r'sixième|septième|huitième|neuvième|dixième)'


FRENCH_PATTERNS = [
    # French chapter patterns with titles
    Pattern(
        regex=r'^Chapitre\s+(\d+)\.\s+(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        language="french",
        capture_groups={1: 'number', 2: 'title'},
        priority=150,
        description="Chapitre 1. Titre"
    ),
    Pattern(
        regex=r'^CHAPITRE\s+(\d+)\.\s+(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        language="french",
        capture_groups={1: 'number', 2: 'title'},
        priority=150,
        description="CHAPITRE 1. Titre"
    ),
    Pattern(
        regex=r'^Chapitre\s+(' + ROMAN + r')\.\s+(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        language="french",
        capture_groups={1: 'number', 2: 'title'},
        priority=150,
        description="Chapitre I. Titre"
    ),
    Pattern(
        regex=r'^CHAPITRE\s+(' + ROMAN + r')\.\s+(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        language="french",
        capture_groups={1: 'number', 2: 'title'},
        priority=150,
        description="CHAPITRE I. Titre"
    ),
    
    # French chapter with separators
    Pattern(
        regex=r'^Chapitre\s+(' + ROMAN + r')\s*[:\-—]\s*(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        language="french",
        capture_groups={1: 'number', 2: 'title'},
        priority=140,
        description="Chapitre I: Titre"
    ),
    Pattern(
        regex=r'^CHAPITRE\s+(' + ROMAN + r')\s*[:\-—]\s*(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        language="french",
        capture_groups={1: 'number', 2: 'title'},
        priority=140,
        description="CHAPITRE I: Titre"
    ),
    Pattern(
        regex=r'^Chapitre\s+(\d+)\s*[:\-—]\s*(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        language="french",
        capture_groups={1: 'number', 2: 'title'},
        priority=140,
        description="Chapitre 1: Titre"
    ),
    Pattern(
        regex=r'^CHAPITRE\s+(\d+)\s*[:\-—]\s*(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        language="french",
        capture_groups={1: 'number', 2: 'title'},
        priority=140,
        description="CHAPITRE 1: Titre"
    ),
    
    # French chapter number only
    Pattern(
        regex=r'^Chapitre\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        language="french",
        capture_groups={1: 'number'},
        priority=120,
        description="Chapitre I"
    ),
    Pattern(
        regex=r'^CHAPITRE\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        language="french",
        capture_groups={1: 'number'},
        priority=120,
        description="CHAPITRE I"
    ),
    Pattern(
        regex=r'^Chapitre\s+(\d+)\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        language="french",
        capture_groups={1: 'number'},
        priority=120,
        description="Chapitre 1"
    ),
    Pattern(
        regex=r'^CHAPITRE\s+(\d+)\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        language="french",
        capture_groups={1: 'number'},
        priority=120,
        description="CHAPITRE 1"
    ),
    
    # French book divisions
    Pattern(
        regex=r'^Livre\s+(' + FRENCH_NUMBER_WORDS + r')\s*$',
        pattern_type=PatternType.LIVRE,
        number_type=NumberType.WORD,
        language="french",
        capture_groups={1: 'number'},
        priority=100,
        description="Livre premier"
    ),
    Pattern(
        regex=r'^LIVRE\s+(' + FRENCH_NUMBER_WORDS + r')\s*$',
        pattern_type=PatternType.LIVRE,
        number_type=NumberType.WORD,
        language="french",
        capture_groups={1: 'number'},
        priority=100,
        description="LIVRE PREMIER"
    ),
    Pattern(
        regex=r'^Livre\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.LIVRE,
        number_type=NumberType.ROMAN,
        language="french",
        capture_groups={1: 'number'},
        priority=100,
        description="Livre I"
    ),
    Pattern(
        regex=r'^LIVRE\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.LIVRE,
        number_type=NumberType.ROMAN,
        language="french",
        capture_groups={1: 'number'},
        priority=100,
        description="LIVRE I"
    ),
]


GERMAN_PATTERNS = [
    # German chapter patterns
    Pattern(
        regex=r'^Kapitel\s+(\d+)\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        language="german",
        capture_groups={1: 'number'},
        priority=120,
        description="Kapitel 1"
    ),
    Pattern(
        regex=r'^KAPITEL\s+(\d+)\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        language="german",
        capture_groups={1: 'number'},
        priority=120,
        description="KAPITEL 1"
    ),
    Pattern(
        regex=r'^Kapitel\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        language="german",
        capture_groups={1: 'number'},
        priority=120,
        description="Kapitel I"
    ),
    Pattern(
        regex=r'^KAPITEL\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        language="german",
        capture_groups={1: 'number'},
        priority=120,
        description="KAPITEL I"
    ),
    
    # German story patterns
    Pattern(
        regex=r'^Die Geschichte\s+(.+)$',
        pattern_type=PatternType.STORY,
        number_type=NumberType.NONE,
        language="german",
        capture_groups={1: 'title'},
        priority=90,
        description="Die Geschichte vom..."
    ),
]


# Combine all international patterns
INTERNATIONAL_PATTERNS = FRENCH_PATTERNS + GERMAN_PATTERNS