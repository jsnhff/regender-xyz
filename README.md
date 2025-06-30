# regender-xyz

A command-line tool for analyzing and transforming gender representation in literature using multiple LLM providers.

## Overview

This tool uses AI (OpenAI or Grok) to identify characters in text and transform gender representation while preserving narrative coherence. It features a powerful book parser that handles 100+ text formats including standard chapters, international languages, plays, and more with intelligent token-based chunking for optimal API usage.

## Features

- **Multi-Provider LLM Support**: Choose between OpenAI and Grok APIs
  - Automatic provider detection based on available API keys
  - Provider-specific model optimization
  - Unified interface for seamless switching
- **Advanced Book Preprocessing**: Convert any text book to clean JSON format
  - Supports 100+ book formats (English, French, German, plays, letters, etc.)
  - Smart chapter/section detection with pattern priority system
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
- **[Parser Architecture](docs/development/CLEAN_PARSER_ARCHITECTURE.md)** - Details on the modular parser
- **[Development Docs](docs/development/)** - Parser development and improvements
- **[Maintenance Docs](docs/maintenance/)** - System maintenance guides

## Requirements

- Python 3.9+
- API key for at least one LLM provider:
  - OpenAI API key (set as `OPENAI_API_KEY`)
  - Grok API key (set as `GROK_API_KEY`)
- **Supported Models:**
  - OpenAI: GPT-4, GPT-4o, GPT-4o-mini
  - Grok: grok-beta, grok-3-mini-fast

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
python regender_cli.py transform text.txt -t feminine

# Explicitly use OpenAI
python regender_cli.py transform text.txt -t feminine --provider openai

# Explicitly use Grok
python regender_cli.py transform text.txt -t feminine --provider grok

# Use a specific model
python regender_cli.py transform text.txt -t feminine --provider openai --model gpt-4
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
├── api_client.py        # Unified LLM client (OpenAI/Grok)
├── model_configs.py     # Model-specific configurations
├── token_utils.py       # Token counting and smart chunking
├── regender_cli.py      # Main CLI entry point
├── regender_json_cli.py # JSON-based processing CLI
├── gutenberg_cli.py     # Simple Gutenberg download/process CLI
├── book_to_json.py      # Book preprocessing interface
├── analyze_characters.py # Character analysis
├── gender_transform.py  # Multi-provider gender transformation
├── json_transform.py    # JSON-based transformation with smart chunking
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

## Recent Updates

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