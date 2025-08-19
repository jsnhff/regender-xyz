# System Architecture & Pipeline

## Overview

Regender-XYZ transforms gender representation in literature using AI. The system follows a clear pipeline:

```
Text File → Parse to JSON → Analyze Characters → Transform Gender → Output Files
```

## Complete Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        regender_book_cli.py                         │
│                    (Unified CLI Entry Point)                        │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │         'regender' command            │
        │    (Complete automated pipeline)      │
        └───────────────────┬───────────────────┘
                            │
    ┌───────────────────────┴───────────────────────┐
    │                                               │
    ▼                                               ▼
┌─────────────────┐                        ┌─────────────────┐
│  Text Input     │                        │  JSON Input     │
│  (.txt file)    │                        │  (.json file)   │
└────────┬────────┘                        └────────┬────────┘
         │                                          │
         ▼                                          │
┌─────────────────────────┐                         │
│   1. PARSING STAGE      │                         │
├─────────────────────────┤                         │
│ book_parser/            │                         │
│ • 100+ formats support  │                         │
│ • Pattern detection     │                         │
│ • Paragraph preservation│                         │
└────────┬────────────────┘                         │
         │                                          │
         └──────────────────┬───────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────┐
│           2. CHARACTER ANALYSIS                   │
├───────────────────────────────────────────────────┤
│ book_characters/                                  │
│ • Flagship-quality prompts only                   │
│ • Identifies all characters & genders             │
│ • Smart chunking for large books                  │
│ • Rate limiting for APIs                          │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────┐
│           3. TRANSFORMATION                       │
├───────────────────────────────────────────────────┤
│ book_transform/                                   │
│ • Applies gender changes                          │
│ • Uses character context                          │
│ • Preserves narrative structure                   │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────┐
│           4. QUALITY CONTROL                      │
├───────────────────────────────────────────────────┤
│ book_transform/quality_control.py                 │
│ • Scans for missed transformations                │
│ • Iterative corrections                           │
│ • Validation scoring                              │
└─────────────────────┬─────────────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────────────┐
│           5. OUTPUT GENERATION                    │
├───────────────────────────────────────────────────┤
│ • Saves transformed JSON                          │
│ • Recreates readable text                         │
│ • Generates transformation report                 │
└───────────────────────────────────────────────────┘
```

## Core Components

### 1. Book Parser (`book_parser/`)
Converts any text format to structured JSON.

```
book_parser/
├── parser.py              # Main BookParser class
├── patterns/             # Format detection
│   ├── standard.py      # English (CHAPTER, Part)
│   ├── international.py # French, German
│   └── plays.py        # Drama (ACT, SCENE)
└── detectors/           # Smart section detection
```

**Capabilities:**
- 100% success rate on Project Gutenberg
- Handles 100+ text formats
- Preserves paragraph structure
- Smart abbreviation handling

### 2. Character Analysis (`book_characters/`)
Identifies all characters using flagship AI models.

**Key Features:**
- Pure LLM analysis (no regex)
- Flagship prompts for accuracy
- Smart chunking for large books
- Rate limiting support

### 3. Transformation Engine (`book_transform/`)
Applies gender transformations using character context.

**Components:**
- `transform.py` - Main orchestration
- `unified_transform.py` - Complete pipeline
- `quality_control.py` - Post-transform validation
- `chunking/` - Token-aware text splitting

### 4. LLM Integration (`api_client.py`)
Unified interface for AI providers.

**Supported Providers:**
- **OpenAI**: GPT-4o, GPT-4o-mini
- **Anthropic**: Claude Opus 4, Claude 3.5 Sonnet
- **Grok**: Grok-4-latest (256k), Grok-3-latest (131k)

## Data Structures

### Input Text
```
CHAPTER I
The Beginning

Alice was very tired. She had been sitting by her sister for a long time.

The White Rabbit appeared suddenly...
```

### Parsed JSON Structure
```json
{
  "metadata": {
    "title": "Alice in Wonderland",
    "author": "Lewis Carroll",
    "date": "1865",
    "source": "Project Gutenberg",
    "processing_note": "Parsed with modular book parser",
    "format_version": "2.0"
  },
  "chapters": [{
    "number": "I",
    "title": "The Beginning",
    "type": "chapter",
    "paragraphs": [
      {
        "sentences": [
          "Alice was very tired.",
          "She had been sitting by her sister for a long time."
        ]
      },
      {
        "sentences": [
          "The White Rabbit appeared suddenly..."
        ]
      }
    ],
    "sentence_count": 3,
    "word_count": 25
  }],
  "statistics": {
    "total_chapters": 12,
    "total_paragraphs": 450,
    "total_sentences": 2300,
    "total_words": 27500
  }
}
```

### Character Analysis
```json
{
  "characters": {
    "Alice": {
      "name": "Alice",
      "gender": "female",
      "role": "protagonist"
    }
  }
}
```

### Transformed Output
```json
{
  "chapters": [{
    "paragraphs": [{
      "sentences": [
        "Alan was very tired..."
      ]
    }]
  }],
  "transformation": {
    "type": "all_male",
    "changes": ["Alice → Alan"]
  }
}
```

## Directory Structure

```
regender-xyz/
├── api_client.py          # LLM provider interface
├── regender_book_cli.py   # CLI entry point
├── book_parser/           # Text parsing module
├── book_characters/       # Character analysis
├── book_transform/        # Transformation engine
├── book_downloader/       # Gutenberg downloads
├── config/
│   └── models.json       # Model configurations
├── books/
│   ├── texts/           # Input text files
│   ├── json/            # Parsed JSON files
│   └── output/          # Transformed output
└── docs/                # Documentation
```

## Key Design Decisions

1. **Flagship Models Only** - Character analysis uses only top-tier models to minimize errors
2. **Mandatory Character Analysis** - Ensures consistency across transformations
3. **Unified Pipeline** - Single command handles entire workflow
4. **Provider Abstraction** - Easy switching between AI providers
5. **Smart Chunking** - Optimizes for each model's context window

## Performance Characteristics

- **Parsing**: ~1-2 seconds per book
- **Character Analysis**: ~2-5 minutes (depends on book size)
- **Transformation**: ~5-10 minutes per book
- **Quality Control**: ~1-3 minutes per iteration

## Configuration

Environment variables in `.env`:
```bash
# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROK_API_KEY=xai-...

# Settings
DEFAULT_PROVIDER=anthropic
DEFAULT_QUALITY_LEVEL=standard
```

## Error Handling

- **Graceful Degradation**: Continues processing other chapters if one fails
- **Automatic Retries**: Failed API calls retry with backoff
- **Rate Limit Management**: Automatic pausing for rate-limited APIs
- **Validation**: Each stage validates its output