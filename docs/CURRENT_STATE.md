# Current State of Regender-XYZ System

*Last Updated: January 2025*

## Overview

Regender-XYZ is a sophisticated command-line tool for analyzing and transforming gender representation in literature using multiple Large Language Model (LLM) providers. The system has evolved to include character analysis, quality control loops, and support for rate-limited APIs.

## Core Architecture

### 1. Entry Points

#### Primary CLI: `regender_book_cli.py`
The main command-line interface supporting:
- `download` - Download books from Project Gutenberg
- `process` - Convert text files to JSON format
- `analyze-characters` - Extract character data using AI
- `transform` - Apply gender transformations
- `list` - List available books
- `validate` - Validate JSON files

#### Quality Control: `run_review_loop.py`
A newer addition that provides post-processing quality control:
- Scans transformed text for missed gendered language
- Uses AI to suggest and apply corrections
- Creates `_qc.txt` files with quality-controlled output
- Currently supports `all_male` and `all_female` (not `gender_swap`)

### 2. Module Structure

```
regender-xyz/
├── api_client.py              # Unified LLM interface
├── book_parser/               # Text to JSON conversion
│   ├── __init__.py           # Main parser interface
│   ├── patterns/             # Format detection
│   │   ├── standard.py       # Standard book formats
│   │   ├── international.py  # Non-English formats
│   │   └── plays.py          # Play/script formats
│   ├── detectors/            # Smart detection
│   │   └── section_detector.py # Enhanced sentence boundaries
│   ├── formatters/           # Output formatting
│   └── utils/                # Validation & batch processing
├── book_transform/           # Gender transformation
│   ├── __init__.py          # Main transform interface
│   ├── chunking/            # Token-based chunking
│   └── validation/          # Quality checks
├── book_characters/         # Character analysis (refactored)
│   ├── analyzer.py          # Core character analysis
│   ├── rate_limited_analyzer.py # New rate-limited support
│   ├── smart_chunked_analyzer.py # Context-preserving chunks
│   ├── context.py           # Character mapping utilities
│   ├── loader.py            # Character data loading
│   └── exporter.py          # Export to CSV/graphs
├── review_loop.py           # Quality control system
└── config/
    └── models.json          # Model configurations
```

### 3. Supported Models & Providers

#### OpenAI
- **gpt-4o**: 128k context, JSON mode support
- **gpt-4o-mini**: 128k context, 16k output

#### Grok
- **grok-4-latest**: 256k context, 16k tokens/min rate limit
- **grok-3-latest**: 131k context
- **grok-beta**: 131k context
- **grok-3-mini-fast**: 131k context

#### MLX (Local)
- **mistral-7b-v0.2**: 32k context
- **mistral-small**: 131k context (requires 45GB RAM)

## Current Workflows

### 1. Standard Transformation Pipeline
```
Text File → Parser → JSON → Transform → Output Text
```

### 2. Character-Aware Transformation
```
JSON → Character Analysis → Character Context → Transform → Output
```

### 3. Quality Control Pipeline
```
Transformed Text → Error Detection → AI Corrections → QC Output
```

### 4. Rate-Limited Analysis (New)
```
Large Book → Smart Chunks → Rate-Limited API → Merged Results
```

## Recent Changes & Refactoring

### Transform Type Standardization
- Consolidated to three types: `all_male`, `all_female`, `gender_swap`
- Removed legacy types like `masculine`, `feminine`, `neutral`
- Consistent naming across all modules

### Character Analysis Improvements
- Removed scanner module - now pure LLM approach
- Added `RateLimitedAnalyzer` for Grok-4's 16k token/minute limit
- Smart chunking preserves context between API calls
- Support for pre-analyzed character files

### Parser Enhancements
- Improved sentence boundary detection
- Better handling of edge cases (abbreviations, quotes)
- Enhanced support for international formats

### Quality Control System
- New `review_loop.py` module for post-processing
- AI-powered detection of missed transformations
- Iterative correction with configurable max iterations
- Detailed logging of all changes

## Data Flow

### 1. Book Processing
```
Raw Text → BookParser → {
  "title": "...",
  "author": "...",
  "chapters": [{
    "title": "...",
    "paragraphs": ["...", "..."]
  }]
}
```

### 2. Character Analysis
```
Book JSON → Character Analyzer → {
  "characters": [{
    "name": "...",
    "gender": "male|female|unknown",
    "context": ["...", "..."]
  }]
}
```

### 3. Transformation
```
Book JSON + Transform Type + Characters (optional) → 
  Chunked Processing → 
  LLM Transformation → 
  Validation → 
  Output Text
```

### 4. Quality Control
```
Transformed Text → 
  Pattern Scanning → 
  AI Error Detection → 
  Corrections → 
  Final QC Text
```

## Current Issues & Limitations

### 1. Rate Limiting
- Grok-4 limited to 16k tokens/minute
- Requires careful chunk management for large books
- Rate limits are per-team, not per-key

### 2. Transform Types
- Quality control doesn't directly support `gender_swap`
- Some edge cases in pronoun detection
- Context window limitations for very large chapters

### 3. Character Analysis
- Depends heavily on LLM quality
- May miss minor characters
- Gender detection based on context can be imperfect

### 4. Output Quality
- Some transformations may miss nested quotes
- Possessive pronouns can be tricky
- Names in dialogue attribution need special handling

## Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your-key
GROK_API_KEY=your-key
LLM_PROVIDER=openai|grok|mlx
GROK_MODEL=grok-4-latest  # For quality control
```

### Model Selection
- Provider defaults configured in `config/models.json`
- Auto-detection based on environment variables
- Fallback chain: Environment → Provider default → Error

## Testing Infrastructure

- `tests/test_providers.py` - Provider configuration tests
- `tests/test_comprehensive.py` - Full system tests
- `tests/test_end_to_end.py` - Workflow tests
- `tests/test_characters.py` - Character analysis tests
- `tests/test_mlx.py` - Local model tests

## File Organization

```
books/
├── texts/          # Raw downloaded books
├── json/           # Parsed JSON format
├── output/         # Transformed text
└── characters/     # Character analysis data

logs/               # Processing logs
config/             # Model configurations
examples/           # Usage examples
```

## Performance Metrics

- 100% success rate on Project Gutenberg corpus
- Average processing time: 2-5 minutes per book
- Token efficiency: ~75% of context window utilized
- Quality control adds 20-30% processing time

## Next Steps for Consolidation

1. **Unified Pipeline**: Merge standard and quality control workflows
2. **Character Integration**: Make character analysis default for all transforms
3. **Rate Limit Management**: Automatic provider switching on limits
4. **Output Validation**: Built-in quality metrics
5. **Batch Processing**: Parallel processing for multiple books