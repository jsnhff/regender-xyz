# Parser Improvements for International & Special Format Books

## Issue
30 out of 100 Gutenberg books failed to parse chapters, including:
- Les Misérables (French)
- Der Struwwelpeter (German)
- Romeo and Juliet (Play format)
- The Jungle Book (Story collection)
- Epistolary novels (letter format)

## Solution Implemented

### 1. Added Multi-Language Support
- **French**: "Chapitre" and "CHAPITRE" patterns with Roman/Arabic numerals
- **French Books**: "Livre" sections (Livre premier, Livre deuxième, etc.)
- **German**: "Kapitel" and "KAPITEL" patterns

### 2. Added Special Format Support
- **Plays**: ACT and SCENE patterns (e.g., "ACT I", "SCENE II. A Street.")
- **Story Collections**: Pattern for story titles without chapter numbers
- **German Stories**: "Die Geschichte" pattern for Struwwelpeter
- **Epistolary Novels**: "To [recipient]" pattern for letters

### 3. Enhanced Section Types
Added new section types to the enum:
- `ACT` - For plays
- `SCENE` - For plays
- `LETTER` - For epistolary novels
- `STORY` - For story collections
- `LIVRE` - For French book divisions

### 4. Results
- **Les Misérables**: Now detects 70 chapters (was 0)
- **Romeo and Juliet**: Now detects 10 acts and 48 scenes (was 0)
- **The Jungle Book**: Now detects stories as sections (was 0)

## Code Changes
1. Updated `ChapterPatterns.PATTERNS` with 30+ new patterns
2. Added `_pattern_type_to_section_type()` method for proper type mapping
3. Enhanced `SectionType` enum with new types
4. Updated sorting logic to handle all numbered section types

## Impact
This should significantly improve the parsing success rate, especially for:
- Non-English texts
- Classical literature in various formats
- Play scripts
- Story collections
- Epistolary novels

The parser is now more inclusive and can handle a wider variety of literary formats while maintaining backward compatibility with standard chapter formats.