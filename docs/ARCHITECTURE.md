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

**Key Classes:**
- `BaseLLMClient` - Abstract base for providers
- `OpenAIClient` - OpenAI implementation
- `GrokClient` - Grok implementation  
- `UnifiedLLMClient` - Auto-detecting wrapper

**Features:**
- Automatic .env file loading
- Provider auto-detection
- Unified API across providers
- Graceful error handling

### 3. Transformation Pipeline

#### Character Analysis (`analyze_characters.py`)
- Identifies characters and their genders
- Tracks character mentions and relationships
- Provides context for accurate transformations

#### Gender Transformation (`gender_transform.py`)
- Multi-provider implementation supporting OpenAI and Grok
- Handles three transformation types:
  - Feminine (he→she)
  - Masculine (she→he)
  - Neutral (he/she→they)
- Provider selection via parameter or environment
- Backward compatible with original API

#### JSON-Based Processing (`json_transform.py`)
- Chapter-by-chapter transformation
- Intelligent token-based chunking
- Model-aware optimization (via `token_utils.py`)
- Progress tracking and error recovery
- Optimized for large books with minimal API calls

### 4. CLI Interfaces

#### Main CLI (`regender_cli.py`)
```bash
regender_cli.py [analyze|transform|pipeline|preprocess] [options]
```

#### JSON CLI (`regender_json_cli.py`)
```bash
regender_json_cli.py input.json -t feminine -o output.json
```

#### Gutenberg CLI (`gutenberg_cli.py`)
```bash
gutenberg_cli.py [download|process|pipeline|list] [options]
```

### 5. Utilities

#### Core Utils (`utils.py`)
- File I/O operations
- API client management
- Caching system
- Error handling

#### Token Utils (`token_utils.py`)
- Token estimation algorithms
- Smart sentence chunking
- Model-specific optimization
- Cost estimation

#### Model Configs (`model_configs.py`)
- Context window definitions
- Default chunk sizes per model
- Model capability tracking

#### Gutenberg Utils (`gutenberg_utils/`)
- Book downloading from Project Gutenberg
- Batch processing utilities
- Format analysis tools

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
├── gutenberg_texts/    # Downloaded texts (100 books)
├── gutenberg_json/     # Processed JSONs
├── logs/               # Processing logs
├── .cache/             # API response cache
│
# Core modules
├── api_client.py       # Multi-provider LLM support
├── model_configs.py    # Model-specific configurations
├── token_utils.py      # Token counting and chunking
├── analyze_characters.py
├── gender_transform.py  # Multi-provider transformer
├── json_transform.py    # Smart chunking processor
├── book_to_json.py
├── utils.py
│
# CLI tools
├── regender_cli.py
├── regender_json_cli.py
└── gutenberg_cli.py
```

## Configuration

### Environment Variables
```bash
# LLM Provider Configuration
OPENAI_API_KEY=sk-...
GROK_API_KEY=xai-...
LLM_PROVIDER=openai  # or grok

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

### Extension Points
- Custom pattern definitions
- Provider plugins (add new LLM providers)
- Model configurations (add new models)
- Transformation rules engine
- Output format plugins
- Token counting improvements