# Parser Upgrade Plan

## Overview

Our current parser is too simplistic to handle the variety of formats in Project Gutenberg texts. This plan outlines improvements to make it robust and production-ready.

## Current Issues

1. **No Gutenberg metadata removal** - Includes copyright headers/footers
2. **Basic pattern matching** - Misses many chapter/section formats
3. **No hierarchy support** - Can't handle Volume → Chapter or Act → Scene
4. **Poor format detection** - Only checks first 100 lines with simple patterns
5. **No TOC utilization** - Ignores table of contents that could inform structure
6. **No confidence scoring** - Can't tell when detection is uncertain

## Proposed Architecture

```
src/parsers/
├── base.py                 # Base parser interface
├── detector.py             # Format detection engine
├── gutenberg.py            # Gutenberg-specific cleaning
├── patterns/
│   ├── __init__.py
│   ├── chapter_patterns.py # Chapter detection patterns
│   ├── play_patterns.py    # Play format patterns
│   ├── toc_patterns.py     # Table of contents patterns
│   └── section_patterns.py # Generic section patterns
├── parsers/
│   ├── __init__.py
│   ├── standard_parser.py  # Standard novels with chapters
│   ├── play_parser.py      # Plays with acts/scenes
│   ├── multipart_parser.py # Multi-volume works
│   ├── poetry_parser.py    # Poetry collections
│   └── essay_parser.py     # Essays/treatises
└── utils/
    ├── text_cleaning.py     # Text normalization
    ├── hierarchy.py         # Multi-level structure builder
    └── validation.py        # Parse result validation
```

## Implementation Phases

### Phase 1: Gutenberg Cleaning (Day 1)

**Goal**: Remove Project Gutenberg headers/footers and extract metadata

**Tasks**:
1. Detect start/end markers:
   - `*** START OF THE PROJECT GUTENBERG EBOOK`
   - `*** END OF THE PROJECT GUTENBERG EBOOK`
   - `*** START OF THIS PROJECT GUTENBERG EBOOK`
   - `***** This file should be named`
   
2. Extract metadata:
   - Title
   - Author
   - Release date
   - Language
   - Character set encoding

3. Clean text:
   - Remove Gutenberg boilerplate
   - Preserve actual book content
   - Handle variations in marker formats

**Code Location**: `src/parsers/gutenberg.py`

### Phase 2: Enhanced Format Detection (Day 2)

**Goal**: Improve format detection accuracy

**Tasks**:
1. **Expand sampling**:
   - Check first 500 lines (not just 100)
   - Also check for TOC
   - Sample middle sections

2. **Pattern scoring**:
   ```python
   patterns = {
       'chapter': {
           'patterns': [
               r'^CHAPTER\s+[IVX]+',
               r'^Chapter\s+\d+',
               r'^CHAPITRE\s+',  # French
               r'^CAPÍTULO\s+',  # Spanish
           ],
           'weight': 1.0,
           'min_matches': 3
       },
       'act_scene': {
           'patterns': [
               r'^ACT\s+[IVX]+',
               r'^SCENE\s+[ivx]+',
               r'Dramatis Person[aæ]',
           ],
           'weight': 1.5,
           'min_matches': 2
       }
   }
   ```

3. **Confidence scoring**:
   - Return confidence level (0-100)
   - Flag uncertain detections
   - Suggest manual review for low confidence

**Code Location**: `src/parsers/detector.py`

### Phase 3: Table of Contents Parser (Day 3)

**Goal**: Use TOC to understand book structure

**Tasks**:
1. **Detect TOC**:
   - "Contents", "Table of Contents", "INDEX"
   - Usually near beginning
   - Before first chapter

2. **Parse TOC**:
   - Extract chapter/section titles
   - Detect hierarchy (parts, books, chapters)
   - Map TOC to actual content

3. **Use TOC for validation**:
   - Verify detected chapters match TOC
   - Use TOC titles for chapter names
   - Detect missing chapters

**Code Location**: `src/parsers/utils/toc_parser.py`

### Phase 4: Multi-Level Hierarchy (Day 4)

**Goal**: Support complex book structures

**Structure Types**:
```python
{
    'flat': ['Chapter 1', 'Chapter 2'],
    'two_level': {
        'Part I': ['Chapter 1', 'Chapter 2'],
        'Part II': ['Chapter 3', 'Chapter 4']
    },
    'three_level': {
        'Volume I': {
            'Book 1': ['Chapter 1', 'Chapter 2'],
            'Book 2': ['Chapter 3', 'Chapter 4']
        }
    },
    'play': {
        'Act I': ['Scene i', 'Scene ii'],
        'Act II': ['Scene i', 'Scene ii', 'Scene iii']
    }
}
```

**Tasks**:
1. Detect hierarchy markers
2. Build tree structure
3. Maintain reading order
4. Convert to flat structure when needed

**Code Location**: `src/parsers/utils/hierarchy.py`

### Phase 5: Expanded Pattern Library (Day 5)

**Goal**: Handle more text formats

**Pattern Categories**:

1. **Standard Chapters**:
   - `Chapter 1`, `CHAPTER I`, `Chap. 1`
   - `1.`, `I.`, `One`
   - Spelled out: `Chapter One`, `First Chapter`

2. **Parts/Books/Volumes**:
   - `PART ONE`, `Part I`, `Part 1`
   - `BOOK I`, `Book First`
   - `VOLUME 1`, `Vol. I`

3. **Plays**:
   - `ACT I`, `Act One`, `FIRST ACT`
   - `Scene 1`, `SCENE I`, `Sc. i`
   - Stage directions: `[Enter`, `[Exit`, `[Aside]`

4. **Special Formats**:
   - Diary entries: `January 1st`, `Monday, 15th`
   - Letters: `Letter I`, `Epistle 1`
   - Poems: Numbered stanzas or titled poems

**Code Location**: `src/parsers/patterns/`

### Phase 6: Format-Specific Parsers (Day 6-7)

**Goal**: Specialized parsers for each format

1. **StandardParser**: 
   - Novels with chapters
   - Handles prologues, epilogues
   - Preserves paragraph structure

2. **PlayParser**:
   - Extracts character list
   - Preserves stage directions
   - Maintains speaker attributions

3. **MultiPartParser**:
   - Handles volumes/books/parts
   - Maintains hierarchy
   - Cross-references sections

4. **PoetryParser**:
   - Preserves line breaks
   - Groups stanzas
   - Handles numbered poems

5. **EssayParser**:
   - Sections and subsections
   - Preserves formatting
   - Handles footnotes

**Code Location**: `src/parsers/parsers/`

### Phase 7: Testing & Validation (Day 8)

**Goal**: Ensure robust parsing

**Test Cases**:
1. Each book format type
2. Edge cases:
   - Missing chapters
   - Irregular numbering
   - Mixed formats
   - Non-English texts
3. Performance tests
4. Regression tests

**Validation**:
- Chapter count reasonable
- Text not truncated
- Hierarchy preserved
- Special formatting retained

## Success Metrics

1. **Coverage**: Successfully parse 95%+ of Gutenberg books
2. **Accuracy**: Correct chapter detection 98%+ of the time
3. **Performance**: Parse average book in <2 seconds
4. **Confidence**: Flag uncertain parses for review

## Migration Strategy

1. Keep existing parser as fallback
2. Run new parser in parallel initially
3. Compare outputs and measure improvement
4. Gradually switch over as confidence grows
5. Maintain backward compatibility with existing JSON format

## Example: Complex Book Structure

**Input** (Count of Monte Cristo):
```
VOLUME ONE
Chapter 1. Marseilles—The Arrival
Chapter 2. Father and Son
...
VOLUME TWO  
Chapter 25. The Unknown
Chapter 26. The Pont du Gard Inn
```

**Output Structure**:
```json
{
  "title": "The Count of Monte Cristo",
  "author": "Alexandre Dumas",
  "format": "multi_part",
  "confidence": 95,
  "structure": {
    "type": "two_level",
    "parts": [
      {
        "title": "VOLUME ONE",
        "chapters": [
          {
            "number": 1,
            "title": "Marseilles—The Arrival",
            "paragraphs": [...]
          }
        ]
      }
    ]
  }
}
```

## Next Steps

1. Review and approve plan
2. Set up new parser structure
3. Start with Phase 1 (Gutenberg cleaning)
4. Iterate and test with real books
5. Document patterns as we discover them

## Notes

- Prioritize common formats first
- Build pattern library incrementally
- Keep parser modular and extensible
- Log uncertain detections for analysis
- Consider ML-based detection for future