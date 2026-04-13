# regender.xyz

A command-line tool for analyzing and transforming gender representation in literature using AI.

## Overview

regender.xyz uses AI (OpenAI or Anthropic/Claude) to identify characters in books and transform gender representation while preserving narrative coherence. It features an interactive TUI, a powerful book parser that handles diverse text formats, and a deterministic post-processing layer that achieves near-100% accuracy even when API calls fail or time out.

## Quick Start

### Interactive TUI (recommended)

```bash
python regender_cli.py
```

The TUI guides you through the full workflow:
1. Select a book file
2. Choose an AI model
3. Optionally analyze characters
4. Choose a transform type
5. Set options (name mapping, quality control)
6. Export to `.txt`, `.rtf`, or `.json`

### Command Line

```bash
# Transform a book directly
python regender_cli.py books/texts/pg1342.txt all_female

# With a custom name map
python regender_cli.py books/texts/pg1342.txt all_male \
  --name-map '{"Elizabeth":"Elliot","Jane":"James"}'

# Skip quality control for faster output
python regender_cli.py books/texts/pg1342.txt gender_swap --no-qc

# Verbose mode
python regender_cli.py books/texts/pg1342.txt nonbinary -v
```

## Features

- **Interactive TUI**: Full-featured terminal UI with live progress, braille spinner, chapter-by-chapter status, and interactive name-mapping review
- **Model Selection**: Choose from any available OpenAI or Anthropic model before processing; pricing and speed estimates shown inline
- **Multi-Provider LLM Support**: OpenAI and Anthropic, with automatic detection from environment variables
- **Four Transform Types**:
  - `all_male` — convert all characters and gendered language to male
  - `all_female` — convert all characters and gendered language to female
  - `nonbinary` — convert to non-binary/gender-neutral
  - `gender_swap` — swap each character's gender individually
- **Deterministic Post-Processing**: `_apply_term_map()` runs word-boundary regex after every LLM response, guaranteeing coverage of 80+ gendered term pairs (familial, social, occupational, religious, period/colloquial) regardless of LLM behavior
- **Alias Auto-Expansion**: Character aliases (Lizzy → Elizabeth, etc.) are automatically expanded in name maps before transformation
- **Timeout Resilience**: When an API batch times out (e.g. on very long paragraphs), the service automatically retries at sentence level — splitting the paragraph into smaller groups and reassembling results. A final term-map pass over the full chapter catches any remaining failures
- **Character Analysis**: LLM-based character identification with gender detection from pronouns and context, name variant merging, and relationship tracking
- **Quality Control**: Automated accuracy review with an interactive warning review UI before export
- **Export Formats**: Plain text (`.txt`), Rich Text (`.rtf`), and structured JSON (`.json`)
- **Advanced Book Parser**: Handles diverse book formats including illustrated editions, plays, letters, and multiple languages

## Requirements

- Python 3.9+
- At least one API key:
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`

## Installation

```bash
git clone https://github.com/jsnhff/regender-xyz.git
cd regender-xyz
pip install -r requirements.txt

# Add API keys to .env
cp .env.example .env
```

## Configuration

```bash
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_PROVIDER=openai       # or 'anthropic'
DEFAULT_MODEL=gpt-4o-mini     # optional model override
```

## Project Structure

```
regender-xyz/
├── src/
│   ├── services/           # Core business logic
│   │   ├── transform_service.py   # Gender transformation + term maps
│   │   ├── character_service.py   # Character analysis
│   │   ├── parser_service.py      # Book parsing
│   │   └── quality_service.py     # Quality control
│   ├── models/             # Domain models (Book, Character, Transformation)
│   ├── providers/          # LLM provider plugins (OpenAI, Anthropic)
│   ├── cli/                # TUI (tui.py)
│   └── config.json         # Service configuration
├── books/
│   ├── texts/              # Source .txt files
│   └── output/             # Transformed output
├── tests/                  # Test suite
└── regender_cli.py         # Main entry point
```

## Architecture

Service-oriented with dependency injection and a strategy pattern for pluggable parsing, analysis, and transformation algorithms. All LLM calls go through a unified provider interface with async/await and token-aware chunking.

Key design decisions:
- **Term map is the safety net**: idempotent, word-boundary regex pass runs after every LLM chunk and again over the full chapter — no gendered term survives a failed batch
- **Sentence-level retry**: oversized paragraphs that time out are split into ≤10-sentence groups and retried individually, then rejoined
- **Alias expansion**: character name maps are expanded with all known aliases before transformation begins

## Testing

```bash
python -m pytest tests/

# Key tests
python -m pytest tests/test_timeout_retry.py   # timeout resilience
python -m pytest tests/test_end_to_end.py      # full pipeline
```

## License

MIT
