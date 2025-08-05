# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Regender-XYZ is a command-line tool for analyzing and transforming gender representation in literature using multiple LLM providers (OpenAI, Anthropic/Claude, Grok). It processes Project Gutenberg books into structured JSON format and can apply gender transformations.

## Common Commands

### Environment Setup
```bash
# Set up API keys (required - at least one)
export OPENAI_API_KEY='your-key'
export ANTHROPIC_API_KEY='your-key'
export GROK_API_KEY='your-key'
export DEFAULT_PROVIDER='openai'  # or 'anthropic' or 'grok'

# Install dependencies
pip install -r requirements.txt
```

### CLI Usage
```bash
# Download books from Project Gutenberg
python regender_book_cli.py download 1342  # Pride and Prejudice

# Process text to JSON
python regender_book_cli.py process books/texts/pg1342.txt

# Analyze characters in a book
python regender_book_cli.py analyze-characters books/json/pg1342.json

# Transform gender representation
python regender_book_cli.py transform books/json/pg1342.json --type all_male

# List available books
python regender_book_cli.py list

# Validate JSON structure
python regender_book_cli.py validate books/json/pg1342.json
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Test specific providers
python tests/test_providers.py

# Test character analysis
python tests/test_characters.py

# End-to-end tests
python tests/test_end_to_end.py
```

## Architecture

### Core Modules

1. **book_parser/** - Modular parsing engine
   - `patterns/` - Format detection (standard.py, international.py, plays.py)
   - `detectors/` - Smart section detection
   - `formatters/` - JSON/text output formatting
   - `utils/` - Validation and batch processing

2. **book_transform/** - AI transformation pipeline
   - `chunking/` - Token-based intelligent chunking
   - `validation/` - Transformation quality checks

3. **book_characters/** - Character analysis system
   - Uses flagship-quality prompts exclusively for accuracy
   - Identifies characters and their genders with zero tolerance for errors
   - Supports rate-limited analysis for large books

4. **api_client.py** - Unified LLM interface
   - Auto-detects provider from environment
   - Handles rate limiting and retries
   - Supports OpenAI, Anthropic/Claude, and Grok models

### Data Flow

1. **Text → JSON**: Books are parsed into paragraph-preserving JSON with metadata
2. **Character Analysis**: LLMs analyze text to identify characters and genders
3. **Transformation**: Gender representations are transformed based on type
4. **Validation**: Results are validated for quality and consistency

### Model Configuration

The `config/models.json` file defines:
- Supported models and their context windows
- Provider-specific settings and rate limits
- Chunking strategies per model
- Model tiers and capabilities

### Key Design Patterns

- **Provider Abstraction**: All LLM calls go through unified api_client
- **Smart Chunking**: Token-aware splitting respects paragraph boundaries
- **Graceful Degradation**: Falls back to simpler parsing for edge cases
- **Rate Limiting**: Built-in support for provider rate limits (e.g., Grok-4)

## Development Notes

- Currently on `book_parser` branch (main branch is `master`)
- No traditional build system - uses plain Python with pip
- Environment variables loaded manually in api_client.py
- Test suite uses unittest-style patterns
- Logs stored in `logs/` directory for debugging