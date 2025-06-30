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
Unified interface for multiple LLM providers.

**Supported Providers:**
- OpenAI (GPT-4, GPT-4o, GPT-4o-mini)
- Grok (grok-beta)

**Key Classes:**
- `BaseLLMClient` - Abstract base for providers
- `OpenAIClient` - OpenAI implementation
- `GrokClient` - Grok implementation  
- `UnifiedLLMClient` - Auto-detecting wrapper

### 3. Transformation Pipeline

#### Character Analysis (`analyze_characters.py`)
- Identifies characters and their genders
- Tracks character mentions and relationships
- Provides context for accurate transformations

#### Gender Transformation (`gender_transform.py`)
- Original OpenAI-only implementation
- Handles three transformation types:
  - Feminine (he→she)
  - Masculine (she→he)
  - Neutral (he/she→they)

#### Multi-Provider Transform (`gender_transform_v2.py`)
- Enhanced version supporting all LLM providers
- Same transformation logic with provider flexibility
- Backward compatible API

#### JSON-Based Processing (`json_transform.py`)
- Chapter-by-chapter transformation
- Progress tracking and error recovery
- Optimized for large books

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
├── analyze_characters.py
├── gender_transform.py  # Original transformer
├── gender_transform_v2.py # Multi-provider version
├── json_transform.py
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
- **Chunk Size**: 50 sentences
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
- Provider plugins
- Transformation rules engine
- Output format plugins