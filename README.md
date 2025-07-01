# regender-xyz

A command-line tool for analyzing and transforming gender representation in literature using multiple LLM providers.

## Overview

This tool uses AI (OpenAI, Grok, or local MLX models) to identify characters in text and transform gender representation while preserving narrative coherence. It features a powerful book parser that handles 100+ text formats including standard chapters, international languages, plays, and more with intelligent token-based chunking for optimal API usage.

## Features

- **Multi-Provider LLM Support**: Choose between OpenAI, Grok, and local MLX models
  - Automatic provider detection based on available API keys
  - Provider-specific model optimization
  - Unified interface for seamless switching
  - **NEW**: Local model support via MLX on Apple Silicon
- **Advanced Book Preprocessing**: Convert any text book to clean JSON format
  - Supports 100+ book formats (English, French, German, plays, letters, etc.)
  - Smart chapter/section detection with pattern priority system
  - **NEW**: Paragraph preservation for maintaining original text structure
  - **NEW**: Intelligent abbreviation handling (Mr., Mrs., Dr., etc.)
  - Artifact removal and intelligent sentence splitting
  - 100% success rate on Project Gutenberg collection
- **Intelligent Token-Based Chunking**: Optimizes API usage for each model
  - Adapts chunk size to model's context window
  - Minimizes API calls while maintaining quality
  - Special handling for models like grok-3-mini-fast
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
- **[Multi-Provider Guide](docs/reference/MULTI_PROVIDER_GUIDE.md)** - Using OpenAI and Grok APIs
- **[MLX Setup Guide](docs/MLX_SETUP.md)** - Running local models on Apple Silicon
- **[JSON Structure Guide](docs/JSON_STRUCTURE.md)** - Understanding the paragraph-aware JSON format
- **[Parser Architecture](docs/development/CLEAN_PARSER_ARCHITECTURE.md)** - Details on the modular parser
- **[Development Docs](docs/development/)** - Parser development and improvements
- **[Maintenance Docs](docs/maintenance/)** - System maintenance guides

## Requirements

- Python 3.9+
- At least one LLM provider:
  - OpenAI API key (set as `OPENAI_API_KEY`)
  - Grok API key (set as `GROK_API_KEY`)
  - MLX local model (Apple Silicon only, set `MLX_MODEL_PATH`)
- **Supported Models:**
  - OpenAI: GPT-4, GPT-4o, GPT-4o-mini
  - Grok: grok-beta, grok-3-mini-fast
  - MLX: Mistral-7B-Instruct (32K context window)

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
python regender_book_cli.py transform books/json/book.json --type comprehensive

# Explicitly use OpenAI
python regender_book_cli.py transform books/json/book.json --provider openai

# Explicitly use Grok
python regender_book_cli.py transform books/json/book.json --provider grok

# Use local MLX model (no API costs)
python regender_book_cli.py transform books/json/book.json --provider mlx
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

### Gender Transformation

Transform books with automatic character analysis:

```bash
# Transform a single book
python regender_book_cli.py transform books/json/book.json --type comprehensive

# Batch transform multiple books
python regender_book_cli.py transform books/json/*.json --type comprehensive --batch
```

### Complete Workflow Example

```bash
# 1. Place your text files in books/texts/
cp ~/my_books/*.txt books/texts/

# 2. Process all text files to JSON
python regender_book_cli.py process

# 3. Transform a specific book
python regender_book_cli.py transform books/json/book.json \
  --type comprehensive \
  --provider mlx \
  --output books/output/book_transformed.json \
  --text books/output/book_transformed.txt
```

## Examples

```bash
# Use local MLX model for transformation (no API costs)
python regender_book_cli.py transform books/json/alice.json \
  --provider mlx \
  --type comprehensive

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
├── api_client.py       # Unified LLM client (OpenAI/Grok/MLX)
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
python regender_book_cli.py transform books/json/Pride_and_Prejudice.json --type comprehensive
```

The Gutenberg downloader automatically handles book metadata and creates properly named files.

## License

MIT

## Recent Updates

### v0.7.0 - Paragraph Preservation & MLX Support
- ✅ Added paragraph preservation in JSON structure
- ✅ Intelligent abbreviation handling (Mr., Mrs., Dr., etc.)
- ✅ Full MLX local model support for offline processing
- ✅ Improved error handling for character analysis
- ✅ Cleaned up codebase - removed obsolete CLI files
- ✅ Consolidated utilities into appropriate modules

### v0.6.0 - Multi-Provider & Smart Chunking
- ✅ Added Grok API support alongside OpenAI
- ✅ Intelligent token-based chunking for optimal API usage
- ✅ Model-specific optimizations (grok-3-mini-fast uses smaller chunks)
- ✅ Unified API client with automatic provider detection
- ✅ Consolidated gender_transform modules

### v0.5.0 - Book Parser Overhaul
- ✅ Modular parser architecture with 100% success rate
- ✅ Support for 100+ book formats and languages
- ✅ Pattern registry system with priorities

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