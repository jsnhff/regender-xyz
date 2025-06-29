# regender-xyz Documentation

## Book Processing Pipeline

### Core Documentation

1. **[Comprehensive Project Summary](COMPREHENSIVE_PROJECT_SUMMARY.md)**
   - Complete overview of the clean book processing pipeline
   - Technical evolution from v1 to v3
   - Quality metrics and performance data
   - Usage examples and code snippets

2. **[Integration Summary](INTEGRATION_SUMMARY.md)**
   - How the book processor integrates with the CLI
   - New `preprocess` command details
   - Architecture and components overview
   - Testing instructions

3. **[Book Format Lessons](BOOK_FORMAT_LESSONS.md)**
   - Learnings from processing different books
   - Format variations (Pride & Prejudice vs Moby Dick)
   - Pattern matching challenges and solutions
   - Recommendations for improvements

4. **[Chapter Chunking Analysis](chapter_chunking_analysis.md)**
   - Original analysis of the regender-xyz codebase
   - How books are processed for gender transformation
   - Chapter detection strategies
   - Integration points with existing code

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
    ├── COMPREHENSIVE_PROJECT_SUMMARY.md
    ├── INTEGRATION_SUMMARY.md
    ├── BOOK_FORMAT_LESSONS.md
    └── chapter_chunking_analysis.md
```