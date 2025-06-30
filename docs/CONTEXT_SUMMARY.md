# Context Summary - Regender-XYZ System

## Overview

Regender-XYZ is a comprehensive system for analyzing and transforming gender representation in literature, featuring advanced book parsing, multi-provider LLM support, and flexible transformation pipelines.

## Key Achievements

### 1. Modular Book Parser (100% Success Rate)
- **Location**: `book_parser/` module
- **Capabilities**: Supports 100+ book formats including international languages, plays, letters
- **Performance**: ~1-2 seconds per book with deterministic output

### 2. Multi-Provider LLM Support
- **Providers**: OpenAI (GPT-4, GPT-4o) and Grok (grok-beta)
- **Architecture**: Abstract base class with unified interface
- **Configuration**: Environment-based with automatic provider detection

### 3. Three CLI Interfaces
- **Main CLI** (`regender_cli.py`): analyze, transform, pipeline, preprocess
- **JSON CLI** (`regender_json_cli.py`): Chapter-by-chapter processing
- **Gutenberg CLI** (`gutenberg_cli.py`): Download and process Project Gutenberg books

## CLI Commands

```bash
# Preprocess any book to JSON
python regender_cli.py preprocess book.txt

# Transform with provider selection
python regender_cli.py transform book.txt -t feminine --provider grok

# Process Gutenberg collection
python gutenberg_cli.py pipeline

# JSON-based transformation
python regender_json_cli.py book.json -t masculine -o output.json
```

## Architecture Highlights

### Pattern Registry System
```
book_parser/patterns/
├── base.py          # Core enums and Pattern class
├── registry.py      # Pattern management
├── standard.py      # English patterns (120+ priority)
├── international.py # French, German (120+ priority)
└── plays.py        # Drama formats (100+ priority)
```

### Provider Architecture
```python
BaseLLMClient (abstract)
├── OpenAIClient
└── GrokClient
     ↓
UnifiedLLMClient (auto-detecting wrapper)
```

## Performance Metrics

### Book Parser
- **Success Rate**: 100% on 100 Gutenberg books
- **Format Coverage**: 72 standard + 28 edge cases handled
- **Speed**: 1-2 seconds per book

### Transformation Pipeline
- **Chunk Size**: 50 sentences per API call
- **Caching**: 24-hour response cache
- **Error Recovery**: Chapter-level with validation

## Documentation Structure

```
docs/
├── development/     # Parser development guides
├── maintenance/     # Cleanup and maintenance docs
├── reference/       # Architecture and API docs
└── *.md            # Legacy docs from book processing
```

## Recent Enhancements

1. **Gutenberg Integration**: Download and process 100 books with one command
2. **Multi-Provider Support**: Seamless switching between OpenAI and Grok
3. **Modular Parser**: Replaced monolithic parser with extensible pattern system
4. **Unified CLIs**: Consolidated functionality into three focused tools

## Configuration

```bash
# API Keys (choose one or both)
OPENAI_API_KEY=sk-...
GROK_API_KEY=xai-...
LLM_PROVIDER=openai  # or grok
```