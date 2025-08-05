# Book Parser Module

This module converts text books into structured JSON format while preserving paragraph structure and handling diverse book formats.

## Overview

The book parser is the foundation of the regender-xyz system. It takes raw text files and converts them into a structured JSON format that preserves the author's intended structure while making the content accessible for AI transformation.

## Module Structure

```
book_parser/
├── parser.py              # Main BookParser class
├── patterns/             # Format detection patterns
│   ├── standard.py      # English formats (CHAPTER, Part)
│   ├── international.py # French, German, etc.
│   └── plays.py        # Drama formats (ACT, SCENE)
├── detectors/           # Smart section detection
│   └── section_detector.py
├── formatters/          # Output formatting
│   ├── json_formatter.py  # JSON output
│   └── text_formatter.py  # Text recreation
└── utils/               # Utilities
    ├── batch_processor.py # Process multiple books
    ├── validator.py       # Validate JSON output
    └── recreate_text.py   # Convert JSON back to text
```

## Key Features

### 1. Format Detection
- Supports 100+ book formats automatically
- Pattern priority system for accurate chapter detection
- Handles standard chapters, acts/scenes, letters, parts, etc.
- International format support (French, German, Spanish)

### 2. Paragraph Preservation
- Maintains original paragraph structure
- Preserves author's intended formatting
- Accurate sentence boundary detection
- Smart handling of abbreviations (Mr., Mrs., Dr., etc.)

### 3. Robust Processing
- Cleans Project Gutenberg artifacts
- Handles various text encodings
- Validates output structure
- Can recreate original text from JSON

## Usage

### Python API

```python
from book_parser import BookParser

# Parse a single book
parser = BookParser()
book_data = parser.parse_file("book.txt")

# Save to JSON
from book_parser import save_book_json
save_book_json(book_data, "book.json")
```

### Command Line

```bash
# Process single file
python regender_book_cli.py process book.txt -o book.json

# Process directory
python regender_book_cli.py process books/texts --output books/json
```

## Output Format

See the [Architecture documentation](../docs/ARCHITECTURE.md) for detailed JSON structure.

## Pattern System

The parser uses a priority-based pattern system:

1. **Standard Patterns** - Common English formats
2. **International Patterns** - Non-English books
3. **Play Patterns** - Dramatic works
4. **Fallback** - Simple paragraph detection

Each pattern defines how to detect chapters and clean content for that format type.

## Validation

The parser includes validation to ensure:
- Valid JSON structure
- Preserved content (no data loss)
- Correct paragraph/sentence counts
- Ability to recreate original text

## Integration

Works seamlessly with other modules:
- `book_downloader` provides input text files
- `book_characters` analyzes the parsed JSON
- `book_transform` processes the structured data