# regender-xyz

A command-line tool for analyzing and transforming gender representation in literature using AI.

## Overview

This tool uses AI (ChatGPT or Claude) to identify characters in books and transform gender representation while preserving narrative coherence. It features a powerful book parser that handles diverse text formats and uses intelligent chunking for optimal API usage.

## Quick Start

Transform any book with a single command:

```bash
# Transform a book with automatic quality control
python regender_cli.py regender book.txt --type all_female

# Test without using API credits
python regender_cli.py regender book.txt --dry-run
```

The `regender` command handles everything automatically:
1. 📖 Parses text to structured JSON
2. 🔍 Analyzes all characters
3. 🔄 Transforms gender with context
4. ✅ Runs quality control iterations
5. 📊 Validates and scores output
6. 💾 Saves both JSON and text formats

## Features

- **Multi-Provider LLM Support**: Choose between OpenAI and Anthropic/Claude
  - Automatic provider detection based on available API keys
  - Provider-specific model optimization
  - Unified interface for seamless switching
  - Support for latest models including Claude Opus 4
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
  - `nonbinary` - Convert all characters to non-binary/gender-neutral
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

# Default provider (optional)
DEFAULT_PROVIDER=openai  # or 'anthropic'
```

See `.env.example` for all configuration options.

## Usage

### Primary Workflow - Single Command

Use the `regender` command for the complete transformation:

```bash
# Transform any book (text or JSON)
python regender_cli.py regender book.txt --type all_female

# Specify provider
python regender_cli.py regender book.txt --provider anthropic

# Test without API usage
python regender_cli.py regender book.txt --dry-run
```

### Alternative Workflows

For more control, you can use individual commands:

```bash
# Download books from Project Gutenberg
python regender_cli.py download 1342  # Pride and Prejudice

# Process text to JSON
python regender_cli.py process book.txt -o book.json

# Analyze characters separately
python regender_cli.py analyze-characters book.json -o characters.json

# Transform with pre-analyzed characters
python regender_cli.py transform book.json --characters characters.json
```

### Transformation Types

- `all_male` - Convert all characters to male
- `all_female` - Convert all characters to female
- `nonbinary` - Convert all characters to non-binary/gender-neutral
- `gender_swap` - Swap each character's gender

### Provider Selection

```bash
# Use default provider (auto-detected from .env)
python regender_cli.py regender book.txt

# Explicitly use a provider
python regender_cli.py regender book.txt --provider openai
python regender_cli.py regender book.txt --provider anthropic
```

## Project Structure

```
regender-xyz/
├── books/               # All book files
│   ├── texts/          # Source text files
│   ├── json/           # Parsed JSON files
│   └── output/         # Transformed books
├── src/
│   ├── services/       # Parser, Character, Transform, Quality
│   ├── strategies/     # Parsing, analysis, transform, quality strategies
│   ├── providers/      # OpenAI, Anthropic LLM clients
│   ├── models/         # Book, Chapter, Character, Transformation
│   ├── parsers/        # Gutenberg, play, integrated parser
│   ├── cli/            # TUI, display, interactive
│   └── exporters.py    # Plain text, RTF export
├── regender_cli.py     # Main CLI entry point
└── docs/               # Documentation
```

## Examples

### Quick Examples

```bash
# Download a specific book
python regender_cli.py download 1342  # Pride and Prejudice

# Transform with unified command
python regender_cli.py regender books/texts/pg1342-Pride_and_Prejudice.txt --type all_female

# Batch transform multiple books
for book in books/texts/*.txt; do
    python regender_cli.py regender "$book" --type gender_swap
done
```


## License

MIT

## Roadmap & Milestones

### Release 1: Complete Pride and Prejudice (Uniform Gender Swap)
- **Goal:** Transform the entire text of Pride and Prejudice by uniformly swapping all gendered language (pronouns, titles, etc.), with no character-specific choices. Keep it simple and consistent for the whole book.
- **Testing Plan:**
  - [x] Fix JSON parsing error in API response handling (markdown/JSON extraction in character_service)
  - [ ] Run gender swap transformation on the full novel text
  - [ ] Spot-check key scenes (opening, ball, proposal)
  - [ ] Validate pronoun, title, and relationship consistency throughout
  - [ ] Prepare print-ready manuscript for book design with Matt Bucknall
- **Remaining for print-ready:**
  - [ ] Optional: Full-novel verification step (e.g. large-context model) to catch cross-chapter consistency
  - [ ] Text export options for InDesign: Plain ASCII (avoid UTF-8 import issues), and Rich Text with `_word_` → `<i>word</i>` for italics via character styles
- **Milestone:** Print-ready version for book design collaboration

### Release 2: Website & Open Source Launch
- **Goal:** Launch a public website to open source the uniform gender-swapped version and sell print-on-demand copies.
- **Testing Plan:**
  - [ ] Website displays transformed book and project info
  - [ ] Print-on-demand integration works (test order flow)
  - [ ] Repo/documentation for public collaboration

### Release 3: Feature Improvements & Expansion
- **Goal:** Add advanced features and support for more books.
- **Testing Plan:**
  - [ ] Character-specific naming/gender choice
  - [ ] Interactive transformation options
  - [ ] Test on additional public domain works (Emma, Jane Eyre, etc.)
  - [ ] Enhanced validation, analytics, and visualization tools

---

## Completed

### Core Platform & Service Architecture
- [x] Service-oriented architecture: ParserService, CharacterService, TransformService, QualityService with strategy pattern
- [x] Main CLI entry point (`regender_cli.py`) with TUI when run with no args
- [x] Character analysis and gender transformation with OpenAI and Anthropic
- [x] Output written once at end (full transformation in memory; no chunk-by-chunk file writes)
- [x] Chapter-by-chapter transform with count validation; no boundary gaps in current pipeline
- [x] Quality control: AdaptiveQualityStrategy with consistency checks, completeness, and iterative correction
- [x] Pronoun validator, gender-neutral (nonbinary) with Mx. titles, relationship possessives
- [x] Ruff linting/formatting and Claude hooks for code quality

### Bill’s Contributions (refactors, agents, pipeline)
- [x] Major refactors: parser, character_service, phase 2–4 refactors, QC fixes
- [x] Real LLM transformation and CLI support for targeting specific characters
- [x] Character analysis with rate limiting; merge of book_parser branch
- [x] Agent definitions and repo maintenance tooling

### Recent (progress, export, TUI, JSON fix)
- [x] Progress tracking (ProgressContext, Stage enum) and export utilities (plain text, RTF for InDesign)
- [x] Polished TUI (Textual): progress bars, book analysis, character selection, LLM setup check
- [x] JSON parsing fix: strip markdown code blocks from LLM responses in character_service
- [x] Default LLM models updated to latest versions
