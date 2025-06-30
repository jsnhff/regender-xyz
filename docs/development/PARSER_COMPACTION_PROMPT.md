# Parser Compaction Prompt

## Context
We have a book parser (`book_to_json.py`) that has grown organically to support many different book formats from Project Gutenberg. Before adding support for the remaining 28 edge-case books, we need to compact and refactor the parser to be more maintainable.

## Current State
The parser currently handles:
1. **Standard Chapters**: CHAPTER I, Chapter 1, etc. (multiple variations)
2. **International**: Chapitre (French), Kapitel (German), etc.
3. **Play Formats**: ACT I, SCENE II, etc.
4. **Story Collections**: Story titles without numbers
5. **Special Sections**: EPILOGUE, APPENDIX, ETYMOLOGY, etc.
6. **Book Divisions**: Part I, Livre premier (French), etc.
7. **Epistolary**: "To [recipient]" patterns

## Refactoring Goals

### 1. Pattern Organization
- Group patterns by category (standard, international, plays, etc.)
- Create a data structure that maps patterns to their metadata
- Consider using a pattern registry or factory pattern
- Make it easy to add new patterns without modifying core logic

### 2. Pattern Definition Structure
Each pattern should have:
```python
{
    'regex': r'^CHAPTER\s+(\d+)\.?\s*$',
    'type': 'chapter',
    'subtype': 'arabic',
    'language': 'english',
    'capture_groups': {
        1: 'number',
        2: 'title'  # if present
    },
    'priority': 100,  # for conflict resolution
    'description': 'Standard English chapter with Arabic numerals'
}
```

### 3. Modular Components
Break down the current monolithic parser into:
- **Pattern Registry**: Manages all regex patterns
- **Section Detector**: Finds sections in text
- **Section Classifier**: Determines section types
- **Content Extractor**: Extracts and cleans section content
- **Structure Builder**: Assembles the final book structure

### 4. Configuration-Driven
Move patterns to a configuration file or class:
```python
PATTERN_CONFIGS = {
    'english': {
        'chapter': [
            {'pattern': r'^CHAPTER\s+(\d+)', 'number_type': 'arabic'},
            {'pattern': r'^Chapter\s+([IVXL]+)', 'number_type': 'roman'},
        ],
        'part': [...],
    },
    'french': {
        'chapter': [
            {'pattern': r'^Chapitre\s+([IVXL]+)', 'number_type': 'roman'},
        ],
        'book': [
            {'pattern': r'^Livre\s+(premier|deuxième|...)', 'number_type': 'word'},
        ],
    },
    # ... more languages and types
}
```

### 5. Edge Cases to Consider
Before compaction, understand these remaining patterns we need to support:
1. **Multi-line Headers**: Where ACT and SCENE are on separate lines
2. **Nested Structures**: Books within books, parts within acts
3. **Mixed Languages**: Books that switch between languages
4. **No Clear Sections**: Technical texts, continuous narratives
5. **Verse/Poetry**: Different line-based structures
6. **Dialogue-Heavy**: Plays with character names as sections

### 6. Testing Strategy
Create test cases for:
- Each pattern type with minimal examples
- Edge cases and ambiguous patterns
- Pattern priority and conflict resolution
- International character handling
- Performance with large texts

### 7. Performance Considerations
- Compile regex patterns once and reuse
- Use more efficient pattern matching for common cases
- Consider lazy evaluation for large texts
- Profile the current implementation to find bottlenecks

### 8. API Design
The refactored parser should have a clean API:
```python
parser = BookParser()
parser.register_patterns(STANDARD_PATTERNS)
parser.register_patterns(INTERNATIONAL_PATTERNS)
parser.register_patterns(PLAY_PATTERNS)

# Parse with options
book = parser.parse(text, options={
    'detect_language': True,
    'merge_small_sections': True,
    'fallback_to_paragraphs': True
})
```

### 9. Backwards Compatibility
Ensure the refactored parser:
- Produces the same output format
- Maintains the same command-line interface
- Handles all currently supported patterns
- Provides migration path for extensions

### 10. Documentation Requirements
Document:
- Pattern format and how to add new patterns
- Language/format detection logic
- Section type hierarchy
- Configuration options
- Performance characteristics

## Code Smells to Address

1. **Long Pattern Lists**: Current PATTERNS list is getting unwieldy
2. **Repeated Logic**: Similar handling for different pattern types
3. **Hard-coded Values**: Magic numbers and strings throughout
4. **Complex Conditionals**: Deep nesting in pattern matching logic
5. **Mixed Responsibilities**: Parser does too many things

## Suggested Refactoring Approach

1. **Extract Pattern Management**
   - Create `PatternRegistry` class
   - Move all patterns to configuration
   - Implement pattern priority system

2. **Separate Concerns**
   - Text preprocessing (cleanup, normalization)
   - Structure detection (finding sections)
   - Content extraction (getting section text)
   - Output formatting (creating JSON)

3. **Improve Testability**
   - Make components independently testable
   - Create fixtures for each book format
   - Add regression tests for current functionality

4. **Add Extensibility Points**
   - Plugin system for custom patterns
   - Hooks for pre/post processing
   - Custom section handlers

## Example Refactored Structure

```
book_parser/
├── __init__.py
├── patterns/
│   ├── __init__.py
│   ├── registry.py          # Pattern management
│   ├── standard.py          # English patterns
│   ├── international.py     # Other language patterns
│   ├── plays.py            # Drama-specific patterns
│   └── special.py          # Edge cases
├── detectors/
│   ├── __init__.py
│   ├── section_detector.py  # Find sections
│   ├── toc_detector.py      # TOC handling
│   └── metadata_extractor.py # Title, author, etc.
├── processors/
│   ├── __init__.py
│   ├── text_cleaner.py      # Text normalization
│   ├── sentence_splitter.py # Sentence detection
│   └── content_extractor.py # Section content
├── builders/
│   ├── __init__.py
│   └── book_builder.py      # Assemble final structure
└── parser.py                # Main API
```

## Metrics for Success

1. **Code Reduction**: Aim for 30-40% fewer lines through better abstraction
2. **Pattern Addition**: Adding new pattern should be <5 lines of code
3. **Performance**: No regression in parsing speed
4. **Test Coverage**: >90% coverage of pattern matching logic
5. **Maintainability**: Clear separation of concerns, documented patterns

## Next Steps After Compaction

Once refactored, adding support for remaining books becomes trivial:
1. Analyze the 28 remaining books
2. Define their patterns in configuration
3. Add test cases
4. Register patterns with the parser

This approach ensures sustainable growth as we handle more edge cases.