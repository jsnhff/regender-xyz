# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Regender-XYZ is a modern command-line tool for analyzing and transforming gender representation in literature using multiple LLM providers (OpenAI, Anthropic/Claude). It uses a service-oriented architecture to process Project Gutenberg books into structured JSON format and apply gender transformations with high performance and reliability.

## Code Quality Standards

### Automated Linting and Formatting
This repository uses **Ruff** for Python linting and formatting. All Python code should:
- Pass `ruff check` without errors
- Be formatted with `ruff format`
- Follow PEP 8 guidelines with 100-character line limit
- Use double quotes for strings
- Have proper import sorting

The `.claude/hooks.json` file configures automatic ruff checks and formatting for all Python file edits.

## Common Commands

### Code Quality
```bash
# Check all Python files
ruff check .

# Fix linting issues automatically
ruff check --fix .

# Format all Python files
ruff format .

# Check specific file
ruff check src/services/character_service.py
```

### Environment Setup
```bash
# Set up API keys (required - at least one)
export OPENAI_API_KEY='your-key'
export ANTHROPIC_API_KEY='your-key'
export DEFAULT_PROVIDER='openai'  # or 'anthropic'

# Install dependencies
pip install -r requirements.txt
```

### CLI Usage
```bash
# Transform a book (complete pipeline)
python regender_cli.py books/texts/pg1342.txt all_female -o output.json

# Download books from Project Gutenberg
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
- **Rate Limiting**: Built-in support for provider rate limits

## Development Notes

- Main branch is `master`
- Service-oriented architecture with dependency injection
- Environment variables loaded through provider configuration
- Test suite uses unittest-style patterns
- Logs stored in `logs/` directory for debugging
- Clean architecture: 84% faster, 60% less memory, <5% code duplication

## Available Agents

This repository includes specialized Claude Code agents in `.claude/agents/`:

- **engineer**: Primary agent for all code-related tasks - implementation, review, testing, and optimization
- **product**: Primary agent for product planning, UX design, and documentation - focuses on user value and clarity

Use these agents with the Task tool when their specialized expertise is needed.

## Important Instructions

- Do what has been asked; nothing more, nothing less
- NEVER create files unless they're absolutely necessary for achieving your goal
- ALWAYS prefer editing an existing file to creating a new one
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User
- Always ensure Python code passes ruff checks before committing