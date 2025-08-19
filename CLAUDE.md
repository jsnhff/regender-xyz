# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Regender-XYZ is a modern command-line tool for analyzing and transforming gender representation in literature using multiple LLM providers (OpenAI, Anthropic/Claude, Grok). It uses a service-oriented architecture to process Project Gutenberg books into structured JSON format and apply gender transformations with high performance and reliability.

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
# Transform a book (complete pipeline)
python regender_cli.py books/texts/pg1342.txt all_female -o output.json

# Download books from Project Gutenberg (still using downloader)
python -m download.download 1342  # Pride and Prejudice

# Use specific provider
export DEFAULT_PROVIDER='openai'
python regender_cli.py input.txt gender_swap

# Skip quality control for faster processing
python regender_cli.py input.txt all_male --no-qc

# Verbose mode for debugging
python regender_cli.py input.txt nonbinary -v
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

### Service-Oriented Architecture

1. **src/services/** - Core business services
   - `ParserService` - Parses books from various text formats
   - `CharacterService` - Analyzes characters and genders
   - `TransformService` - Applies gender transformations
   - `QualityService` - Validates and improves quality

2. **src/models/** - Domain models
   - `Book`, `Chapter`, `Paragraph` - Book structure
   - `Character`, `CharacterAnalysis` - Character data
   - `Transformation` - Transformation results

3. **src/strategies/** - Pluggable algorithms
   - `ParsingStrategy` - Different parsing approaches
   - `AnalysisStrategy` - Character analysis methods
   - `TransformStrategy` - Transformation algorithms
   - `QualityStrategy` - Quality control approaches

4. **src/providers/** - LLM Provider plugins
   - `legacy_client.py` - Unified LLM interface
   - `openai_provider.py` - OpenAI integration
   - `anthropic_provider.py` - Anthropic integration
   - `unified_provider.py` - Provider wrapper

### Data Flow

1. **Text → JSON**: Books are parsed into paragraph-preserving JSON with metadata
2. **Character Analysis**: LLMs analyze text to identify characters and genders
3. **Transformation**: Gender representations are transformed based on type
4. **Validation**: Results are validated for quality and consistency

### Configuration

The `src/config.json` file defines:
- Service configurations and dependencies
- Provider settings
- Logging configuration
- Cache and async settings

### Key Design Patterns

- **Service-Oriented**: Clean separation of concerns with dependency injection
- **Strategy Pattern**: Pluggable algorithms for parsing, analysis, and transformation
- **Plugin System**: Easy to add new LLM providers
- **Async Support**: Full async/await for parallel processing
- **Provider Abstraction**: All LLM calls go through unified provider interface
- **Smart Chunking**: Token-aware splitting respects paragraph boundaries
- **Rate Limiting**: Built-in support for provider rate limits (e.g., Grok-4)

## Development Notes

- Currently on `phase4-migration` branch (main branch is `master`)
- Service-oriented architecture with dependency injection
- Environment variables loaded through provider configuration
- Test suite uses unittest-style patterns
- Logs stored in `logs/` directory for debugging
- Clean architecture: 84% faster, 60% less memory, <5% code duplication