# regender-xyz

A command-line tool for analyzing and transforming gender representation in literature using AI.

## Overview

This tool uses AI (OpenAI, Anthropic/Claude, or Grok) to identify characters in books and transform gender representation while preserving narrative coherence. It features a powerful book parser that handles diverse text formats and uses intelligent chunking for optimal API usage.

## Quick Start

Transform any book with a single command:

```bash
# Transform a book with automatic quality control
python regender_book_cli.py regender book.txt --type all_female

# High quality mode with extensive validation
python regender_book_cli.py regender book.txt --quality high

# Test without using API credits
python regender_book_cli.py regender book.txt --dry-run
```

The `regender` command handles everything automatically:
1. 📖 Parses text to structured JSON
2. 🔍 Analyzes all characters
3. 🔄 Transforms gender with context
4. ✅ Runs quality control iterations
5. 📊 Validates and scores output
6. 💾 Saves both JSON and text formats

## Features

- **Multi-Provider LLM Support**: Choose between OpenAI, Anthropic/Claude, and Grok
  - Automatic provider detection based on available API keys
  - Provider-specific model optimization
  - Unified interface for seamless switching
  - Support for latest models including Claude Opus 4 and Grok-4
- **Advanced Book Preprocessing**: Convert any text book to clean JSON format
  - Supports diverse book formats (English, French, German, plays, letters, etc.)
  - Smart chapter/section detection with pattern priority system
  - Paragraph preservation for maintaining original text structure
  - Enhanced abbreviation handling for accurate sentence boundaries
  - Artifact removal and intelligent sentence splitting
- **Intelligent Token-Based Chunking**: Optimizes API usage for each model
  - Adapts chunk size to model's context window
  - Minimizes API calls while maintaining quality
  - Smart chunking strategy for comprehensive book coverage
- **Character Analysis**: Advanced LLM-based character identification
  - Pure LLM analysis for better accuracy
  - Gender detection from pronouns and context
  - Name variant merging and relationship tracking
  - Handles complex character networks
- **Gender Transformation**: Transform text using different modes
  - `all_male` - Convert all characters to male
  - `all_female` - Convert all characters to female
  - `gender_swap` - Swap each character's gender
  - Character-aware transformations for consistency
  - Preserves exact sentence and paragraph structure
- **Quality Control**: Integrated validation and correction
  - Multiple QC iterations based on quality level
  - Automatic detection and fixing of missed transformations
  - Quality scoring and reporting
- **Flexible Usage**: Multiple ways to work
  - Single command transformation with `regender`
  - Step-by-step processing for fine control
  - Batch processing for multiple books
  - Dry-run mode for testing without API usage

## Documentation

- **[Documentation Index](docs/README.md)** - Start here for overview
- **[Workflow Guide](docs/WORKFLOW.md)** - How to use the system
- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design and data structures
- **[Providers Guide](docs/PROVIDERS.md)** - Using different AI providers

## Requirements

- Python 3.9+
- At least one LLM provider API key:
  - OpenAI (`OPENAI_API_KEY`)
  - Anthropic (`ANTHROPIC_API_KEY`)
  - Grok (`GROK_API_KEY`)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/regender-xyz.git
cd regender-xyz

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Edit `.env` with your API keys and preferences:

```bash
# API Keys (at least one required)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
GROK_API_KEY=your-grok-api-key

# Default provider (optional)
DEFAULT_PROVIDER=openai  # or 'anthropic' or 'grok'
```

See `.env.example` for all configuration options.

## Usage

### Primary Workflow - Single Command

Use the `regender` command for the complete transformation:

```bash
# Transform any book (text or JSON)
python regender_book_cli.py regender book.txt --type all_female

# Specify provider
python regender_book_cli.py regender book.txt --provider anthropic

# High quality mode
python regender_book_cli.py regender book.txt --quality high

# Test without API usage
python regender_book_cli.py regender book.txt --dry-run
```

### Alternative Workflows

For more control, you can use individual commands:

```bash
# Download books from Project Gutenberg
python regender_book_cli.py download 1342  # Pride and Prejudice

# Process text to JSON
python regender_book_cli.py process book.txt -o book.json

# Analyze characters separately
python regender_book_cli.py analyze-characters book.json -o characters.json

# Transform with pre-analyzed characters
python regender_book_cli.py transform book.json --characters characters.json
```

### Transformation Types

- `all_male` - Convert all characters to male
- `all_female` - Convert all characters to female  
- `gender_swap` - Swap each character's gender

### Provider Selection

```bash
# Use default provider (auto-detected from .env)
python regender_book_cli.py regender book.txt

# Explicitly use a provider
python regender_book_cli.py regender book.txt --provider openai
python regender_book_cli.py regender book.txt --provider anthropic
python regender_book_cli.py regender book.txt --provider grok
```

## Project Structure

```
regender-xyz/
├── books/               # All book files
│   ├── texts/          # Source text files
│   ├── json/           # Parsed JSON files  
│   └── output/         # Transformed books
├── book_parser/         # Book parsing system
│   ├── patterns/       # Format detection patterns
│   ├── detectors/      # Smart section detection
│   └── utils/          # Validation and batch processing
├── book_downloader/    # Project Gutenberg downloader
├── book_transform/     # AI transformation system
│   ├── chunking/       # Smart token-based chunking
│   └── quality_control.py  # Integrated QC system
├── book_characters/    # Character analysis module
├── api_client.py       # Unified LLM client
├── regender_book_cli.py # Main CLI interface
└── docs/               # Documentation
```

## Examples

### Quick Examples

```bash
# Download a specific book
python regender_book_cli.py download 1342  # Pride and Prejudice

# Transform with unified command
python regender_book_cli.py regender books/texts/pg1342-Pride_and_Prejudice.txt --type all_female

# Batch transform multiple books
for book in books/texts/*.txt; do
    python regender_book_cli.py regender "$book" --type gender_swap
done
```

### Quality Levels

- `fast` - No quality control, quickest results
- `standard` - One QC iteration (default)
- `high` - Three QC iterations, best quality

## License

MIT