# regender-xyz

A command-line tool for analyzing and transforming gender representation in literature using multiple LLM providers.

## Overview

This tool uses AI (OpenAI or Grok) to identify characters in text and transform gender representation while preserving narrative coherence. It features a powerful book parser that handles 100+ text formats including standard chapters, international languages, plays, and more with intelligent token-based chunking for optimal API usage.

## Features

- **Multi-Provider LLM Support**: Choose between OpenAI and Grok
  - Automatic provider detection based on available API keys
  - Provider-specific model optimization
  - Unified interface for seamless switching
  - **NEW**: Grok-4-latest with 256k context window support
- **Advanced Book Preprocessing**: Convert any text book to clean JSON format
  - Supports 100+ book formats (English, French, German, plays, letters, etc.)
  - Smart chapter/section detection with pattern priority system
  - Paragraph preservation for maintaining original text structure
  - **IMPROVED**: Enhanced abbreviation handling (Mr., Mrs., Dr., etc.) with better sentence boundary detection
  - Artifact removal and intelligent sentence splitting
  - 100% success rate on Project Gutenberg collection
- **Intelligent Token-Based Chunking**: Optimizes API usage for each model
  - Adapts chunk size to model's context window
  - Minimizes API calls while maintaining quality
  - **NEW**: Smart chunking strategy for comprehensive book coverage with Grok
  - Numbered sentence approach for perfect alignment
- **Smart Character Analysis**: Advanced LLM-based character identification
  - **NEW**: Pure LLM analysis (regex scanning removed for better accuracy)
  - **NEW**: Strategic chunk analysis for complete character coverage
  - Gender detection from pronouns and context
  - Name variant merging and relationship tracking
  - Handles 100+ characters per book
- **Gender Transformation**: Transform text using different gender representations
  - Feminine transformation (male → female)
  - Character-aware transformations for consistency
  - **NEW**: Preserves exact sentence and paragraph structure
  - **NEW**: Handles complex names (Harry → Harriet)
- **Pre-analyzed Character Support**: Use saved character analysis for faster processing
  - Analyze once, transform multiple times
  - Share character data across projects
- **JSON-based Processing**: Work with pre-parsed books for better control
- **Beautiful CLI**: Colorful interface with progress animations

## Documentation

- **[Complete Flow Diagram](docs/reference/COMPLETE_FLOW_DIAGRAM.md)** - Visual overview of the entire system
- **[Transformation Pipeline](docs/reference/TRANSFORMATION_PIPELINE.md)** - Detailed transformation process
- **[Transformation Modes](docs/reference/TRANSFORMATION_MODES.md)** - Understanding all_male, all_female, and gender_swap modes
- **[Character Analysis Module](book_characters/README.md)** - Smart character extraction system
- **[Multi-Provider Guide](docs/reference/MULTI_PROVIDER_GUIDE.md)** - Using OpenAI and Grok
- **[JSON Structure Guide](docs/JSON_STRUCTURE.md)** - Understanding the paragraph-aware JSON format
- **[Parser Architecture](docs/development/CLEAN_PARSER_ARCHITECTURE.md)** - Details on the modular parser
- **[Development Docs](docs/development/)** - Parser development and improvements
- **[Maintenance Docs](docs/maintenance/)** - System maintenance guides

## Requirements

- Python 3.9+
- At least one LLM provider:
  - OpenAI API key (set as `OPENAI_API_KEY`)
  - Grok API key (set as `GROK_API_KEY`)
- **Supported Models:**
  - OpenAI: GPT-4o, GPT-4o-mini
  - Grok: grok-4-latest (256k context), grok-3-latest (131k context), grok-beta, grok-3-mini-fast

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/regender-xyz.git
cd regender-xyz

# Install dependencies
pip install -r requirements.txt
# Or manually:
pip install openai requests beautifulsoup4 python-dotenv

# Set up API keys (choose one or both)
export OPENAI_API_KEY='your-openai-api-key'
export GROK_API_KEY='your-grok-api-key'

# Optional: specify default provider
export LLM_PROVIDER='openai'  # or 'grok'
```

## Multi-Provider LLM Support

The system now supports multiple LLM providers for flexibility and redundancy:

### Configure Providers

1. **Copy the example configuration:**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env with your API keys**

3. **Test your configuration:**
   ```bash
   python tests/test_providers.py
   ```

### Using Different Providers

```bash
# Use default provider (auto-detected or from LLM_PROVIDER env var)
python regender_book_cli.py transform books/json/book.json --type gender_swap

# Explicitly use OpenAI
python regender_book_cli.py transform books/json/book.json --provider openai

# Explicitly use Grok
python regender_book_cli.py transform books/json/book.json --provider grok
```

## Usage

### Book Processing

Convert any text book to clean JSON format:

```bash
python regender_book_cli.py process --input books/texts --output books/json
```

The parser automatically detects:
- Standard chapters (CHAPTER I, Chapter 1, etc.)
- International formats (Chapitre, Kapitel, etc.)
- Plays (ACT I, SCENE II)
- Letters and diaries
- Story collections
- And many more formats

Options:
- `--input`: Input directory for text files (default: books/texts)
- `--output`: Output directory for JSON files (default: books/json)
- `--verify`: Validate the JSON by recreating text

### Character Analysis

Analyze characters in a book before transformation:

```bash
# Analyze characters using Grok (recommended for large books)
python regender_book_cli.py analyze-characters books/json/book.json \
  --provider grok \
  --output books/json/book_characters.json
```

### Gender Transformation

Transform books with automatic or pre-analyzed characters.

**Available transformation types:**
- `all_male` - Convert ALL characters to male gender (no exceptions)
- `all_female` - Convert ALL characters to female gender (no exceptions)  
- `gender_swap` - Swap each character's gender (male → female, female → male)

Transform books with automatic or pre-analyzed characters:

```bash
# Transform with automatic character analysis
python regender_book_cli.py transform books/json/book.json --type all_male

# Transform using pre-analyzed characters (faster)
python regender_book_cli.py transform books/json/book.json \
  --characters books/json/book_characters.json \
  --type all_female \
  --output books/output/book_transformed.json \
  --text books/output/book_transformed.txt

# Batch transform multiple books
python regender_book_cli.py transform books/json/*.json --type gender_swap --batch
```

### Complete Workflow Example

```bash
# 1. Place your text files in books/texts/
cp ~/my_books/*.txt books/texts/

# 2. Process all text files to JSON
python regender_book_cli.py process

# 3. Transform a specific book
python regender_book_cli.py transform books/json/book.json \
  --type all_male \
  --provider grok \
  --output books/output/book_transformed.json \
  --text books/output/book_transformed.txt
```

## Examples

```bash
# Use Grok for transformation (large context window)
python regender_book_cli.py transform books/json/alice.json \
  --provider grok \
  --type all_female

# Use OpenAI for high-quality transformation
python regender_book_cli.py transform books/json/pride.json \
  --provider openai \
  --model gpt-4o

# Use Grok for fast processing
python regender_book_cli.py transform books/json/gatsby.json \
  --provider grok \
  --model grok-beta
```

## Project Structure

```
regender-xyz/
├── books/               # All book files
│   ├── texts/          # Downloaded text files
│   ├── json/           # Parsed JSON files  
│   └── output/         # Transformed books
├── book_parser/         # Book parsing system
│   ├── patterns/       # Format detection patterns
│   ├── detectors/      # Smart section detection
│   └── utils/          # Validation and batch processing
├── gutenberg/          # Project Gutenberg downloader
├── book_transform/     # AI book transformation system
│   └── chunking/       # Smart token-based chunking
├── api_client.py       # Unified LLM client (OpenAI/Grok)
├── regender_book_cli.py # Main CLI interface
└── docs/               # Documentation
```

## Gutenberg Collection Support

The parser has been tested on 100 Project Gutenberg books with 100% success rate:
- 72 books parse with standard patterns
- 28 edge cases handled with specialized patterns
- Supports multiple languages and formats

### Quick Start with Gutenberg Books

```bash
# Download and process top 100 books
python regender_book_cli.py download --count 100
python regender_book_cli.py process

# Transform a specific book
python regender_book_cli.py transform books/json/Pride_and_Prejudice.json --type gender_swap
```

The Gutenberg downloader automatically handles book metadata and creates properly named files.

## License

MIT

## Recent Updates

### v0.8.0 - Enhanced Character Analysis & Sentence Preservation
- ✅ Pure LLM-based character analysis (removed regex scanning)
- ✅ Smart chunking strategy for Grok's 131k context window
- ✅ Fixed sentence boundary detection for abbreviations
- ✅ Numbered sentence transformation for perfect alignment
- ✅ Pre-analyzed character support for faster processing
- ✅ Handles 100+ characters per book (tested on Harry Potter)
- ✅ Improved name transformations (Harry → Harriet)

### v0.7.0 - Paragraph Preservation
- ✅ Added paragraph preservation in JSON structure
- ✅ Intelligent abbreviation handling (Mr., Mrs., Dr., etc.)
- ✅ Improved error handling for character analysis
- ✅ Cleaned up codebase - removed obsolete CLI files
- ✅ Consolidated utilities into appropriate modules

### v0.6.0 - Multi-Provider & Smart Chunking
- ✅ Added Grok API support alongside OpenAI
- ✅ Intelligent token-based chunking for optimal API usage
- ✅ Model-specific optimizations (grok-3-mini-fast uses smaller chunks)
- ✅ Unified API client with automatic provider detection
- ✅ Consolidated gender_transform modules

## Roadmap

### Release 1: Complete Novel Processing
- [x] Advanced parser supporting 100+ book formats
- [x] Clean JSON preprocessing pipeline
- [x] Multi-provider LLM support (OpenAI & Grok)
- [x] Smart token-based chunking
- [ ] Full novel transformation with consistency
- [ ] Print-ready output generation

### Release 2: Web Interface
- [ ] Public website for transformations
- [ ] API for programmatic access
- [ ] Print-on-demand integration

### Release 3: Advanced Features
- [ ] Additional LLM providers (Claude, Gemini)
- [ ] Character-specific transformations
- [ ] Interactive transformation options
- [ ] Support for more languages
- [ ] Enhanced validation tools