# Documentation Index

This directory contains all project documentation organized by category.

## Development Documentation

Documentation related to development processes, improvements, and refactoring:

- [Parser Compaction Prompt](development/PARSER_COMPACTION_PROMPT.md) - Guidelines for parser compaction process
- [Parser Improvements](development/PARSER_IMPROVEMENTS.md) - Detailed parser improvement documentation
- [Parser Refactoring Complete](development/PARSER_REFACTORING_COMPLETE.md) - Summary of completed parser refactoring

## Maintenance Documentation

Documentation for ongoing maintenance and cleanup tasks:

- [Post Compaction Tasks](maintenance/POST_COMPACTION_TASKS.md) - Tasks to complete after parser compaction
- [Cleanup Summary](maintenance/CLEANUP_SUMMARY.md) - Summary of cleanup activities

## Reference Documentation

Technical reference and analysis documentation:

- [Remaining Patterns Analysis](reference/REMAINING_PATTERNS_ANALYSIS.md) - Analysis of remaining patterns to implement
- [Complete Flow Diagram](reference/COMPLETE_FLOW_DIAGRAM.md) - Complete system flow diagram and architecture

## Book Processing Documentation

Documentation from the original book processing pipeline:

- [Comprehensive Project Summary](COMPREHENSIVE_PROJECT_SUMMARY.md) - Complete overview of the clean book processing pipeline
- [Integration Summary](INTEGRATION_SUMMARY.md) - How the book processor integrates with the CLI
- [Book Format Lessons](BOOK_FORMAT_LESSONS.md) - Learnings from processing different books
- [Chapter Chunking Analysis](chapter_chunking_analysis.md) - Original analysis of the regender-xyz codebase

## Quick Start

### Processing Books

```bash
# Process all text files in books/texts/ to JSON
python regender_book_cli.py process

# Transform a book using local MLX model
python regender_book_cli.py transform books/json/book.json --provider mlx

# Download and process Gutenberg books
python regender_book_cli.py download --count 10
python regender_book_cli.py process
```

### Using the Paragraph-Aware JSON

```python
import json

# Load preprocessed book
with open('books/json/book.json', 'r') as f:
    book = json.load(f)

# Access chapters with paragraph structure
for chapter in book['chapters']:
    print(f"{chapter['title']}: {chapter.get('sentence_count', 0)} sentences")
    
    # Process paragraphs (new structure)
    if 'paragraphs' in chapter:
        for paragraph in chapter['paragraphs']:
            for sentence in paragraph['sentences']:
                # Apply transformations
                transformed = transform_gender(sentence)
    # Handle old structure for compatibility
    elif 'sentences' in chapter:
        for sentence in chapter['sentences']:
            transformed = transform_gender(sentence)
```

## Key Features

- **Fast Processing**: < 1 second for full novels
- **Accurate Chapter Detection**: 100% accuracy for standard formats
- **Paragraph Preservation**: Maintains original text structure
- **Abbreviation Handling**: Correctly handles Mr., Mrs., Dr., etc.
- **Artifact Removal**: Removes EPUB artifacts, brackets, formatting codes
- **Smart Sentence Splitting**: Handles embedded dialogues and abbreviations
- **Multi-Provider Support**: OpenAI, Grok, and local MLX models
- **Clean Output**: JSON format with metadata, paragraphs, and sentence arrays

## File Organization

```
regender-xyz/
├── books/                          # All book files
│   ├── texts/                      # Source text files
│   ├── json/                       # Processed JSON files
│   └── output/                     # Transformed books
├── book_parser/                    # Modular book parsing system
│   ├── parser.py                   # Main parser API
│   ├── patterns/                   # Format detection patterns
│   └── detectors/                  # Smart section detection
├── book_transform/                 # Gender transformation system
│   ├── transform.py                # Main transformation logic
│   ├── character_analyzer.py       # Character analysis
│   ├── llm_transform.py           # LLM integration
│   └── utils.py                   # Utility functions
├── api_client.py                   # Unified LLM client (OpenAI/Grok/MLX)
├── regender_book_cli.py           # Main CLI interface
└── docs/                          # Documentation
    ├── README.md                  # This file
    ├── QUICK_START.md             # Getting started guide
    ├── CHANGELOG.md               # Version history
    ├── JSON_STRUCTURE.md          # JSON format documentation
    ├── development/               # Development-related docs
    ├── maintenance/               # Maintenance docs
    └── reference/                 # Reference docs
```