# regender-xyz Architecture

## Overview

The regender-xyz project processes books from Project Gutenberg, parsing them into structured JSON format and applying gender transformations. The system is designed for batch processing of large text collections.

## Directory Structure

```
regender-xyz/
├── gutenberg_texts/      # Raw text files from Gutenberg (84M)
├── gutenberg_json/       # Processed JSON files (60M)
├── clean_json_books/     # Sample clean JSON outputs
├── docs/                 # Documentation
├── logs/                 # Processing logs
├── output/              # Transformation outputs
└── tests/               # Test files
```

## Core Components

### 1. Book Downloading
- `download_gutenberg_books.py`: Downloads books from Project Gutenberg
- `collect_gutenberg_texts.py`: Organizes downloaded files

### 2. Book Parsing
- `book_parser_v2.py`: Advanced parser supporting 20+ chapter formats
- `book_to_clean_json.py`: Converts parsed books to clean JSON with sentence splitting
- `book_processor.py`: Unified interface for book processing

### 3. Gender Transformation
- `gender_transform.py`: Core transformation engine
- `json_transform.py`: JSON-based transformation pipeline
- `claude_transform.py`: AI-powered transformation using Claude

### 4. CLI Tools
- `regender_cli.py`: Main command-line interface
- `regender_json_cli.py`: JSON-specific CLI operations

### 5. Analysis Tools
- `analyze_book_formats.py`: Analyzes book format patterns
- `analyze_characters.py`: Character gender analysis
- `pronoun_validator.py`: Validates transformation accuracy

## Processing Pipeline

1. **Download**: Fetch books from Project Gutenberg
2. **Parse**: Extract structure (chapters, metadata) from raw text
3. **Clean**: Split into sentences and prepare for transformation
4. **Transform**: Apply gender transformations
5. **Validate**: Check transformation accuracy

## Key Features

- Handles 100+ Gutenberg books automatically
- Detects 20+ chapter format patterns
- 70% success rate for chapter detection
- Processes 10M+ words efficiently
- Modular design for easy extension

## Data Formats

### Input: Raw Text
Plain text files from Project Gutenberg with various formatting styles.

### Intermediate: Parsed JSON
```json
{
  "metadata": {
    "title": "Book Title",
    "source_file": "filename.txt"
  },
  "chapters": [
    {
      "number": "1",
      "title": "Chapter One",
      "sentences": ["First sentence.", "Second sentence."],
      "word_count": 500
    }
  ],
  "statistics": {
    "total_chapters": 20,
    "total_sentences": 5000,
    "total_words": 100000
  }
}
```

### Output: Transformed Text
Gender-transformed versions in JSON or reconstructed text format.

## Performance

- Processes 100 books in ~3 minutes
- Average processing time: 1.8 seconds per book
- Handles books from 3K to 900K+ words

## Extension Points

1. Add new chapter patterns in `book_parser_v2.py`
2. Customize transformation rules in `gender_transform.py`
3. Add new output formats in `assemble_book.py`
4. Extend CLI commands in `regender_cli.py`