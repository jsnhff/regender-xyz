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

### Preprocessing a Book

```bash
# Basic usage - creates clean JSON
python regender_cli.py preprocess book.txt

# With verification file
python regender_cli.py preprocess book.txt --verify

# Specify output location
python regender_cli.py preprocess book.txt -o output/book_clean.json

# Skip dialogue splitting
python regender_cli.py preprocess book.txt --no-fix-sentences
```

### Using the Clean JSON

```python
import json

# Load preprocessed book
with open('book_clean.json', 'r') as f:
    book = json.load(f)

# Access chapters and sentences
for chapter in book['chapters']:
    print(f"{chapter['title']}: {chapter['sentence_count']} sentences")
    
    # Process sentences
    for sentence in chapter['sentences']:
        # Apply transformations
        transformed = transform_gender(sentence)
```

## Key Features

- **Fast Processing**: < 1 second for full novels
- **Accurate Chapter Detection**: 100% accuracy for standard formats
- **Artifact Removal**: Removes EPUB artifacts, brackets, formatting codes
- **Smart Sentence Splitting**: Handles embedded dialogues and abbreviations
- **Clean Output**: JSON format with metadata and sentence arrays

## File Organization

```
regender-xyz/
├── book_to_json.py                 # Complete book processing pipeline
├── regender_cli.py                 # CLI with preprocess command
└── docs/                           # Documentation
    ├── README.md                   # This file
    ├── development/                # Development-related docs
    │   ├── PARSER_COMPACTION_PROMPT.md
    │   ├── PARSER_IMPROVEMENTS.md
    │   └── PARSER_REFACTORING_COMPLETE.md
    ├── maintenance/                # Maintenance docs
    │   ├── POST_COMPACTION_TASKS.md
    │   └── CLEANUP_SUMMARY.md
    ├── reference/                  # Reference docs
    │   ├── REMAINING_PATTERNS_ANALYSIS.md
    │   └── COMPLETE_FLOW_DIAGRAM.md
    ├── COMPREHENSIVE_PROJECT_SUMMARY.md
    ├── INTEGRATION_SUMMARY.md
    ├── BOOK_FORMAT_LESSONS.md
    └── chapter_chunking_analysis.md
```