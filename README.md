# regender-xyz

A command-line tool for analyzing and transforming gender representation in literature.

## Overview

This tool uses AI to identify characters in text and transform gender representation while preserving narrative coherence. It features a powerful book parser that handles 100+ text formats including standard chapters, international languages, plays, and more.

## Features

- **Advanced Book Preprocessing**: Convert any text book to clean JSON format
  - Supports 100+ book formats (English, French, German, plays, letters, etc.)
  - Smart chapter/section detection with pattern priority system
  - Artifact removal and intelligent sentence splitting
  - 100% success rate on Project Gutenberg collection
- **Character Analysis**: Identify characters, their gender, and mentions in text
- **Gender Transformation**: Transform text using different gender representations
  - Feminine transformation (male → female)
  - Masculine transformation (female → male)
  - Gender-neutral transformation
- **JSON-based Processing**: Work with pre-parsed books for better control
- **Verification**: Check for missed transformations
- **Beautiful CLI**: Colorful interface with progress animations

## Documentation

- **[Complete Flow Diagram](docs/reference/COMPLETE_FLOW_DIAGRAM.md)** - Visual overview of the entire system
- **[Parser Architecture](docs/development/CLEAN_PARSER_ARCHITECTURE.md)** - Details on the modular parser
- **[Development Docs](docs/development/)** - Parser development and improvements
- **[Maintenance Docs](docs/maintenance/)** - System maintenance guides

## Requirements

- Python 3.9+
- OpenAI API key (set as environment variable `OPENAI_API_KEY`)
- **Recommended Model:** GPT-4o or GPT-4 (large context windows)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/regender-xyz.git
cd regender-xyz

# Install dependencies
pip install openai
pip install beautifulsoup4  # Optional: for better Gutenberg downloads

# Set your OpenAI API key
export OPENAI_API_KEY='your-api-key'
```

## Usage

### Book Preprocessing

Convert any text book to clean JSON format:

```bash
python regender_cli.py preprocess path/to/book.txt
```

The parser automatically detects:
- Standard chapters (CHAPTER I, Chapter 1, etc.)
- International formats (Chapitre, Kapitel, etc.)
- Plays (ACT I, SCENE II)
- Letters and diaries
- Story collections
- And many more formats

Options:
- `-o, --output`: Specify output JSON file (default: book_clean.json)
- `--verify`: Create verification file by recreating text from JSON
- `-q, --quiet`: Suppress progress messages

### Character Analysis

Analyze a text file to identify characters:

```bash
python regender_cli.py analyze path/to/your/text.txt
```

### Gender Transformation

Transform gender representation in text:

```bash
python regender_cli.py transform path/to/your/text.txt --type feminine
```

### Full Pipeline

Run analysis and transformation together:

```bash
python regender_cli.py pipeline path/to/your/text.txt --type feminine
```

### JSON-Based Processing

For better control over large books, use the JSON workflow:

```bash
# First preprocess to JSON
python regender_cli.py preprocess pride_and_prejudice.txt -o pride.json

# Then transform the JSON
python regender_json_cli.py pride.json -t feminine -o pride_feminine.json

# Optionally recreate as text
python regender_json_cli.py pride_feminine.json --recreate -o pride_feminine.txt
```

## Examples

```bash
# Preprocess a French book
python regender_cli.py preprocess les_miserables.txt

# Transform Alice in Wonderland to masculine
python regender_cli.py transform alice.txt -t masculine -o alan_in_wonderland.txt

# Process a play with gender-neutral transformation
python regender_cli.py pipeline romeo_and_juliet.txt -t neutral
```

## Project Structure

```
regender-xyz/
├── book_parser/          # Modular parser (100% success rate)
│   ├── patterns/        # Pattern definitions for various formats
│   └── detectors/       # Smart section detection
├── gutenberg_utils/     # Project Gutenberg tools
│   ├── download_gutenberg_books.py
│   ├── process_all_gutenberg.py
│   └── README.md       # Detailed utilities documentation
├── regender_cli.py      # Main CLI entry point
├── regender_json_cli.py # JSON-based processing CLI
├── gutenberg_cli.py     # Simple Gutenberg download/process CLI
├── book_to_json.py      # Book preprocessing interface
├── analyze_characters.py # Character analysis
├── gender_transform.py  # Gender transformation
├── json_transform.py    # JSON-based transformation
└── docs/               # Documentation
    ├── development/    # Parser development docs
    ├── maintenance/    # Cleanup and maintenance
    └── reference/      # Architecture and flow diagrams
```

## Gutenberg Collection Support

The parser has been tested on 100 Project Gutenberg books with 100% success rate:
- 72 books parse with standard patterns
- 28 edge cases handled with specialized patterns
- Supports multiple languages and formats

### Quick Start with Gutenberg Books

```bash
# Download and process top 100 books
python gutenberg_cli.py pipeline

# Process a specific Gutenberg book
python regender_json_cli.py gutenberg_json/pg1342-Pride_and_Prejudice_clean.json -t feminine
```

See [gutenberg_utils/README.md](gutenberg_utils/README.md) for detailed documentation.

## License

MIT

## Roadmap

### Release 1: Complete Novel Processing
- [x] Advanced parser supporting 100+ book formats
- [x] Clean JSON preprocessing pipeline
- [ ] Full novel transformation with consistency
- [ ] Print-ready output generation

### Release 2: Web Interface
- [ ] Public website for transformations
- [ ] API for programmatic access
- [ ] Print-on-demand integration

### Release 3: Advanced Features
- [ ] Character-specific transformations
- [ ] Interactive transformation options
- [ ] Support for more languages
- [ ] Enhanced validation tools