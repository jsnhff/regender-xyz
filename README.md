# regender-xyz

A command-line tool for analyzing and transforming gender representation in literature using AI.

## Overview

This tool uses AI (ChatGPT or Claude) to identify characters in books and transform gender representation while preserving narrative coherence. It features a powerful book parser that handles diverse text formats and uses intelligent chunking for optimal API usage.

## Quick Start

Transform any book with a single command:

```bash
# Transform a book with automatic quality control
python regender_book_cli.py regender book.txt --type all_female

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
python regender_book_cli.py regender book.txt --type all_female

# Specify provider
python regender_book_cli.py regender book.txt --provider anthropic

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
├── download/           # Project Gutenberg downloader
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


## License

MIT

## Roadmap & Milestones

### Release 1: Complete Pride and Prejudice (Uniform Gender Swap)
- **Goal:** Transform the entire text of Pride and Prejudice by uniformly swapping all gendered language (pronouns, titles, etc.), with no character-specific choices. Keep it simple and consistent for the whole book.
- **Testing Plan:**
  - [x] Fix JSON parsing error in API response handling ("Unterminated string starting at: line 2 column 11")
  - [ ] Run gender swap transformation on the full novel text
  - [ ] Spot-check key scenes (opening, ball, proposal)
  - [ ] Validate pronoun, title, and relationship consistency throughout
  - [ ] Prepare print-ready manuscript for book design with Matt Bucknall
- **Critical Fixes Needed:**
  - [ ] Fix file writing logic to collect all transformed chunks in memory and write once at the end
  - [ ] Improve chapter boundary handling to ensure complete novel transformation
  - [ ] Implement full novel verification step using GPT-4.1's 1M token context window
  - [ ] Add validation to ensure consistent character representation throughout the novel
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

### Core Platform Development
- [x] **Third major rewrite:** Streamlined the codebase with a CLI-first focus and improved architecture ([77f59c0], [74505b6], [54d31a1])
- [x] Archived and cleaned up legacy versions, moving old code to `/archive` ([74505b6], [54d31a1])
- [x] Created project README and initial documentation ([5d623d5], [1ba486a])
- [x] Set up project structure and repository
- [x] Implemented main CLI entry point (`regender_cli.py`)
- [x] Implemented core character analysis and gender transformation modules
- [x] Added pronoun validator for transformation consistency
- [x] Added support for gender-neutral transformation with Mx. titles
- [x] Added post-processing validation for relationship possessives
- [x] Added colorful CLI visuals and animations
- [x] Implemented gender-themed animated spinners and progress bars
- [x] Fixed OpenAI API JSON format compatibility issue
- [x] Improved pronoun consistency in gender transformations
- [x] Fixed pronoun validator patterns for neutral transformation

### AI Chunking System (June 2025)
- [x] **Bulletproof AI Chunking:** Developed hybrid AI + Python chunking system achieving 100% text coverage
  - [x] Created `ai_chunking.py` module with guaranteed coverage for any Project Gutenberg book
  - [x] Implemented Python regex fallback when AI analysis unavailable
  - [x] Added automatic chapter pattern detection (Roman numerals, numbered chapters, titled chapters)
  - [x] Built size-aware chunking that adapts to book characteristics and respects 32k output limits
  - [x] Tested successfully on Pride & Prejudice (17 chunks) and Moby Dick (140 chunks)
- [x] **Consolidated Pipeline Testing:** Built unified test interface with command-line options
  - [x] Created `test_pipeline.py` with support for different transformation types
  - [x] Added `--save`, `--transform`, and `--all-books` flags for flexible testing
  - [x] Integrated AI chunking with character analysis and gender transformation pipeline
- [x] **Major Codebase Cleanup:** Prepared master branch for clean merge
  - [x] Removed 4,700+ unnecessary files (1.2M+ lines of code/dependencies)
  - [x] Deleted entire virtual environment directories that shouldn't be in git
  - [x] Enhanced .gitignore with comprehensive patterns for future cleanup prevention
  - [x] Preserved core functionality while removing all development cruft
- [x] **Competition-Ready Architecture:** Designed modular system for easy comparison with alternative approaches
  - [x] Separated AI chunking logic into standalone module for A/B testing
  - [x] Created clean APIs for swapping chunking implementations
  - [x] Focused transform logic purely on gender transformation, isolated from chunking concerns
