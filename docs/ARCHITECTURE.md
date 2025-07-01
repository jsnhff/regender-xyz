# Regender-XYZ Architecture

## Overview

Regender-XYZ is a modular system for analyzing and transforming gender representation in literature. The architecture supports multiple LLM providers, advanced book parsing, and flexible transformation pipelines.

## Core Components

### 1. Book Parser Module (`book_parser/`)
A modular parser achieving 100% success rate on Project Gutenberg texts.

```
book_parser/
├── parser.py              # Main API: BookParser class
├── patterns/
│   ├── base.py           # Base pattern definitions
│   ├── registry.py       # Pattern management system
│   ├── standard.py       # English patterns (CHAPTER, Part, etc.)
│   ├── international.py  # French, German patterns
│   └── plays.py         # Drama patterns (ACT, SCENE)
└── detectors/
    └── section_detector.py # Smart section detection
```

**Key Features:**
- Pattern-based chapter detection with priority system
- Support for 100+ book formats
- International language support
- Smart fallback strategies

### 2. LLM Integration (`api_client.py`)
Unified interface for multiple LLM providers with automatic .env loading.

**Supported Providers:**
- OpenAI (GPT-4, GPT-4o, GPT-4o-mini)
- Grok (grok-beta, grok-3-mini-fast)
- MLX (local models on Apple Silicon - Mistral-7B)

**Key Classes:**
- `_BaseLLMClient` - Abstract base for providers (internal)
- `_OpenAIClient` - OpenAI implementation (internal)
- `_GrokClient` - Grok implementation (internal)
- `_MLXClient` - MLX local model implementation (internal)
- `UnifiedLLMClient` - Auto-detecting wrapper (public API)

**Features:**
- Automatic .env file loading
- Provider auto-detection
- Unified API across providers
- Graceful error handling

### 3. Transformation Pipeline (`book_transform/`)

#### Character Analysis (`book_transform/character_analyzer.py`)
- Identifies characters and their genders
- Tracks character mentions and relationships
- Provides context for accurate transformations
- Handles MLX JSON parsing limitations gracefully

#### Gender Transformation (`book_transform/transform.py`)
- Multi-provider implementation supporting OpenAI, Grok, and MLX
- Handles three transformation types:
  - comprehensive (default)
  - names_only
  - pronouns_only
- Provider selection via parameter or environment
- Paragraph-aware processing

#### Smart Chunking (`book_transform/chunking/`)
- Chapter-by-chapter transformation
- Intelligent token-based chunking
- Model-aware optimization
- Progress tracking and error recovery
- Optimized for large books with minimal API calls

### 4. CLI Interface (`regender_book_cli.py`)

Unified command-line interface for all book processing operations:

```bash
# Download books from Project Gutenberg
regender_book_cli.py download --count 10

# Process text files to JSON
regender_book_cli.py process --input books/texts --output books/json

# Transform books
regender_book_cli.py transform books/json/book.json --type comprehensive --provider mlx

# List available books
regender_book_cli.py list

# Validate JSON files
regender_book_cli.py validate
```

### 5. Utilities

#### Book Transform Utils (`book_transform/utils.py`)
- API error handling
- Caching system
- Safe API call decorators

#### Chunking Utilities (`book_transform/chunking/`)
- Token estimation algorithms
- Smart sentence chunking
- Model-specific optimization
- Model configurations

#### Gutenberg Downloader (`gutenberg/`)
- Book downloading from Project Gutenberg
- Metadata extraction
- Automatic file naming

## Data Flow

```
1. Input Stage
   ├── Raw text file (.txt)
   └── Pre-processed JSON

2. Parsing Stage (book_parser/)
   ├── Pattern matching
   ├── Section detection
   └── JSON generation

3. Analysis Stage
   ├── Character identification
   └── Gender detection

4. Transformation Stage
   ├── Provider selection (OpenAI/Grok)
   ├── Chunk processing
   └── Validation

5. Output Stage
   ├── Transformed JSON
   ├── Recreated text
   └── Validation report
```

## Directory Structure

```
regender-xyz/
├── book_parser/          # Modular parser (100% success rate)
│   ├── patterns/        # Pattern definitions
│   └── detectors/       # Detection logic
├── gutenberg_utils/     # Gutenberg-specific tools
│   ├── download_gutenberg_books.py
│   ├── process_all_gutenberg.py
│   └── common.py
├── docs/               # Documentation
│   ├── development/    # Development guides
│   ├── maintenance/    # Maintenance docs
│   └── reference/      # API references
├── tests/              # Test suite
├── books/              # All book files
│   ├── texts/         # Downloaded text files
│   ├── json/          # Processed JSON files
│   └── output/        # Transformed books
├── logs/               # Processing logs
├── .cache/             # API response cache
│
# Core modules
├── api_client.py       # Multi-provider LLM support (OpenAI/Grok/MLX)
├── book_to_json.py     # Book parsing wrapper
├── book_transform/     # Transformation system
│   ├── transform.py   # Main transformation logic
│   ├── character_analyzer.py
│   ├── llm_transform.py
│   ├── utils.py      # Transform utilities
│   └── chunking/     # Smart chunking system
│
# CLI tool
└── regender_book_cli.py  # Unified CLI interface
```

## Configuration

### Environment Variables
```bash
# LLM Provider Configuration
OPENAI_API_KEY=sk-...
GROK_API_KEY=xai-...
MLX_MODEL_PATH=/path/to/mlx/model  # For local MLX models
LLM_PROVIDER=openai  # or grok or mlx

# Optional Settings
REGENDER_DISABLE_CACHE=1
REGENDER_DEBUG=1
```

### Provider Selection Logic
1. Explicit parameter (`--provider`)
2. Environment variable (`LLM_PROVIDER`)
3. Auto-detection (first available)

## Performance Characteristics

### Book Parser
- **Success Rate**: 100% on Gutenberg collection
- **Formats**: 100+ supported patterns
- **Speed**: ~1-2 seconds per book

### LLM Processing
- **Chunk Size**: Model-adaptive (30-100 sentences)
  - grok-3-mini-fast: 30 sentences/chunk
  - gpt-4o-mini: 75 sentences/chunk
  - grok-beta: 100 sentences/chunk
- **Token Awareness**: Estimates actual token usage
- **Caching**: 24-hour response cache
- **Concurrency**: Chapter-level parallelism possible

## Error Handling

### Graceful Degradation
- Provider fallback on API errors
- Chapter-level recovery
- Validation warnings vs errors

### Logging
- Structured logs in `logs/`
- API response caching in `.cache/`
- Progress tracking for long operations

## Security Considerations

- API keys via environment variables only
- No credentials in code or logs
- `.env` files excluded from git
- Secure credential storage recommended

## Future Enhancements

### Planned Features
- Additional LLM providers (Claude, Gemini)
- Streaming API support
- Real-time transformation preview
- Web interface
- Enhanced MLX model support

### Extension Points
- Custom pattern definitions
- Provider plugins (add new LLM providers)
- Model configurations (add new models)
- Transformation rules engine
- Output format plugins
- Token counting improvements