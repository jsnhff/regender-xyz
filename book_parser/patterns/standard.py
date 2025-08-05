"""Standard English pattern definitions"""

from .base import Pattern, PatternType, NumberType


# Roman numeral pattern component
ROMAN = r'[IVXLCDM]+'

# Number words pattern component
NUMBER_WORDS = r'(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|' \
               r'Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|' \
               r'Eighteen|Nineteen|Twenty|Thirty|Forty|Fifty|Sixty|Seventy|' \
               r'Eighty|Ninety|Hundred)'

# Uppercase number words pattern component
NUMBER_WORDS_UPPER = r'(?:ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|' \
                     r'ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|' \
                     r'EIGHTEEN|NINETEEN|TWENTY|THIRTY|FORTY|FIFTY|SIXTY|SEVENTY|' \
                     r'EIGHTY|NINETY|HUNDRED)'


ENGLISH_PATTERNS = [
    # Chapter patterns with titles
    Pattern(
        regex=r'^CHAPTER\s+(\d+)\.\s+(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number', 2: 'title'},
        priority=150,
        description="CHAPTER 1. Title"
    ),
    Pattern(
        regex=r'^Chapter\s+(\d+)\.\s+(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number', 2: 'title'},
        priority=150,
        description="Chapter 1. Title"
    ),
    Pattern(
        regex=r'^CHAPTER\s+(' + ROMAN + r')\.\s+(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number', 2: 'title'},
        priority=150,
        description="CHAPTER I. Title"
    ),
    Pattern(
        regex=r'^Chapter\s+(' + ROMAN + r')\.\s+(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number', 2: 'title'},
        priority=150,
        description="Chapter I. Title"
    ),
    
    # Chapter patterns with separators
    Pattern(
        regex=r'^Chapter\s+(' + ROMAN + r')\s*[:\-—]\s*(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number', 2: 'title'},
        priority=140,
        description="Chapter I: Title"
    ),
    Pattern(
        regex=r'^CHAPTER\s+(' + ROMAN + r')\s*[:\-—]\s*(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number', 2: 'title'},
        priority=140,
        description="CHAPTER I: Title"
    ),
    Pattern(
        regex=r'^Chapter\s+(\d+)\s*[:\-—]\s*(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number', 2: 'title'},
        priority=140,
        description="Chapter 1: Title"
    ),
    Pattern(
        regex=r'^CHAPTER\s+(\d+)\s*[:\-—]\s*(.+)$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number', 2: 'title'},
        priority=140,
        description="CHAPTER 1: Title"
    ),
    
    # Chapter number only
    Pattern(
        regex=r'^Chapter\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=120,
        description="Chapter I"
    ),
    Pattern(
        regex=r'^CHAPTER\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=120,
        description="CHAPTER I"
    ),
    Pattern(
        regex=r'^Chapter\s+(\d+)\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=120,
        description="Chapter 1"
    ),
    Pattern(
        regex=r'^CHAPTER\s+(\d+)\.?\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=120,
        description="CHAPTER 1"
    ),
    Pattern(
        regex=r'^Chapter\s+(' + NUMBER_WORDS + r')\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.WORD,
        capture_groups={1: 'number'},
        priority=110,
        description="Chapter One"
    ),
    Pattern(
        regex=r'^CHAPTER\s+(' + NUMBER_WORDS + r')\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.WORD,
        capture_groups={1: 'number'},
        priority=110,
        description="CHAPTER ONE"
    ),
    Pattern(
        regex=r'^CHAPTER\s+(' + NUMBER_WORDS_UPPER + r')\.\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.WORD,
        capture_groups={1: 'number'},
        priority=115,
        description="CHAPTER ONE."
    ),
    # This pattern is higher priority than the regular CHAPTER ONE pattern
    Pattern(
        regex=r'^CHAPTER\s+(' + NUMBER_WORDS_UPPER + r')\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.WORD,
        capture_groups={1: 'number'},
        priority=125,  # Higher than the lowercase "CHAPTER ONE" pattern
        description="CHAPTER ONE (uppercase)"
    ),
    
    # Alternative formats
    Pattern(
        regex=r'^(' + ROMAN + r')\.\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=50,
        description="I."
    ),
    Pattern(
        regex=r'^(\d+)\.\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=40,
        description="1."
    ),
    
    # Bracketed chapter numbers (like in Ulysses)
    Pattern(
        regex=r'^\[\s*(\d+)\s*\]\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=60,
        description="[ 1 ]"
    ),
    Pattern(
        regex=r'^\[\s*(' + ROMAN + r')\s*\]\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=60,
        description="[ I ]"
    ),
    
    # Bare Roman numerals (like in Metamorphosis)
    Pattern(
        regex=r'^(' + ROMAN + r')\s*$',
        pattern_type=PatternType.CHAPTER,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=30,
        description="I (bare)"
    ),
    
    # Grouped sections (like in Ulysses)
    Pattern(
        regex=r'^—\s*(' + ROMAN + r')\s*—\s*$',
        pattern_type=PatternType.PART,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=80,
        description="— I —"
    ),
    
    # Book patterns (higher level than parts)
    Pattern(
        regex=r'^BOOK\s+(' + ROMAN + r')(?:\s*[:\-—]\s*(.+))?\s*$',
        pattern_type=PatternType.PART,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number', 2: 'title'},
        priority=105,
        description="BOOK I: Title"
    ),
    Pattern(
        regex=r'^Book\s+(' + ROMAN + r')(?:\s*[:\-—]\s*(.+))?\s*$',
        pattern_type=PatternType.PART,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number', 2: 'title'},
        priority=105,
        description="Book I: Title"
    ),
    Pattern(
        regex=r'^BOOK\s+(' + NUMBER_WORDS_UPPER + r')(?:\s*[:\-—]\s*(.+))?\s*$',
        pattern_type=PatternType.PART,
        number_type=NumberType.WORD,
        capture_groups={1: 'number', 2: 'title'},
        priority=105,
        description="BOOK ONE: Title"
    ),
    
    # Part patterns
    Pattern(
        regex=r'^Part\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.PART,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=100,
        description="Part I"
    ),
    Pattern(
        regex=r'^PART\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.PART,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=100,
        description="PART I"
    ),
    Pattern(
        regex=r'^Part\s+(\d+)\.?\s*$',
        pattern_type=PatternType.PART,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=100,
        description="Part 1"
    ),
    Pattern(
        regex=r'^PART\s+(\d+)\.?\s*$',
        pattern_type=PatternType.PART,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=100,
        description="PART 1"
    ),
    
    # Letter patterns
    Pattern(
        regex=r'^To\s+((?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Sir\s+|Lord\s+|Lady\s+|Miss\s+|Master\s+|Dame\s+)[A-Z][^.!?]+)\s*$',
        pattern_type=PatternType.LETTER,
        number_type=NumberType.NONE,
        capture_groups={1: 'title'},
        priority=90,
        description="To Someone (epistolary format)"
    ),
    Pattern(
        regex=r'^Letter\s+(\d+)\.?\s*$',
        pattern_type=PatternType.LETTER,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=90,
        description="Letter 1"
    ),
    Pattern(
        regex=r'^LETTER\s+(\d+)\.?\s*$',
        pattern_type=PatternType.LETTER,
        number_type=NumberType.ARABIC,
        capture_groups={1: 'number'},
        priority=90,
        description="LETTER 1"
    ),
    Pattern(
        regex=r'^Letter\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.LETTER,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=90,
        description="Letter I"
    ),
    Pattern(
        regex=r'^LETTER\s+(' + ROMAN + r')\.?\s*$',
        pattern_type=PatternType.LETTER,
        number_type=NumberType.ROMAN,
        capture_groups={1: 'number'},
        priority=90,
        description="LETTER I"
    ),
    
    # Story collection patterns (generic title - very low priority)
    Pattern(
        regex=r'^([A-Z][^.!?]+[A-Za-z])\s*$',
        pattern_type=PatternType.STORY,
        number_type=NumberType.NONE,
        capture_groups={1: 'title'},
        priority=5,  # Very low priority - only use as last resort
        description="Story Title"
    ),
]