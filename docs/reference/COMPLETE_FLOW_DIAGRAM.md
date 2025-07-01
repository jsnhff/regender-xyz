# Complete Regender-XYZ Flow Diagram

## High-Level Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Raw Text      │     │  Parsed JSON     │     │  Transformed    │
│  (.txt files)   │ --> │  (clean format)  │ --> │    Output       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        |                        |                        |
   Any text format         Clean JSON with          Gender-swapped
   (100+ supported)      chapters & sentences            text
```

## Detailed Flow Chart

```
┌──────────────────────────────────────────────────────────────────┐
│                        ENTRY POINT                               │
├──────────────────────────────────────────────────────────────────┤
│                     regender_book_cli.py                         │
│              (Unified CLI for all operations)                    │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             v
┌────────────────────────────┐  ┌──────────────────────────────────┐
│   PREPROCESSING STAGE      │  │   JSON TRANSFORMATION STAGE      │
├────────────────────────────┤  ├──────────────────────────────────┤
│ book_to_json.py           │  │ book_transform/transform.py      │
│  └─ process_book_to_json() │  │  ├─ transform_book()             │
│                           │  │  ├─ analyze_book_characters()    │
│ Uses book_parser/:        │  │  └─ process chapters             │
│  ├─ PatternRegistry       │  │                                  │
│  ├─ SectionDetector       │  │ For each chapter:                │
│  └─ BookParser API        │  │  ├─ smart chunk sentences        │
│                           │  │  ├─ call LLM API                 │
│ Supports:                 │  │  └─ merge results                │
│  • English chapters       │  │                                  │
│  • French (Chapitre)      │  │                                  │
│  • German (Kapitel)       │  │                                  │
│  • Plays (ACT/SCENE)      │  │                                  │
│  • Letters & Diaries      │  │                                  │
│  • Story collections      │  │                                  │
└────────────┬───────────────┘  └─────────────┬────────────────────┘
             │                                │
             v                                v
┌────────────────────────────────────────────────────────────────┐
│                     LLM API CALLS                              │
├────────────────────────────────────────────────────────────────┤
│ Providers: OpenAI, Grok, MLX (local)                           │
│                                                                │
│ 1. Character Analysis (book_transform/character_analyzer.py)   │
│    └─ Identify characters and their genders                    │
│                                                                │
│ 2. Gender Transformation (book_transform/llm_transform.py)     │
│    └─ Transform gender references                             │
│                                                                │
│ API Request Format:                                            │
│ {                                                              │
│   "model": "gpt-4",                                           │
│   "messages": [                                               │
│     {"role": "system", "content": "transformation prompt"},    │
│     {"role": "user", "content": "text to transform"}         │
│   ],                                                          │
│   "temperature": 0,                                           │
│   "response_format": {"type": "json_object"}                  │
│ }                                                              │
└────────────────────────────────────────────────────────────────┘

## Modular Parser Architecture

```
book_parser/
├── parser.py              # Main API: BookParser class
├── patterns/
│   ├── registry.py       # Pattern management
│   ├── standard.py       # English patterns (CHAPTER, Part, etc.)
│   ├── international.py  # French, German patterns
│   └── plays.py         # Drama patterns (ACT, SCENE)
└── detectors/
    └── section_detector.py # Smart section detection
```

### Pattern Matching Flow:
1. **First Pass**: High-priority patterns (chapters, acts, parts)
2. **Fallback**: Low-priority patterns only if no chapters found
3. **Smart Detection**: Handles multi-line patterns, nested structures

## Data Structures

### Input: Raw Text (Any Format)
```
CHAPTER I.
Down the Rabbit-Hole

Alice was beginning to get very tired...

---OR---

Chapitre I
Dans le terrier du lapin

Alice commençait à se sentir très lasse...

---OR---

ACT I
Scene 1. A public place.
[Enter SAMPSON and GREGORY]
```

### Intermediate: Clean JSON (with Paragraph Structure)
```json
{
  "metadata": {
    "title": "Alice's Adventures in Wonderland",
    "author": "Lewis Carroll",
    "source": "Project Gutenberg",
    "format_version": "2.0"
  },
  "chapters": [
    {
      "number": "I",
      "title": "Down the Rabbit-Hole",
      "type": "chapter",
      "paragraphs": [
        {
          "sentences": [
            "Alice was beginning to get very tired...",
            "She had peeped into the book..."
          ]
        },
        {
          "sentences": [
            "So she was considering in her own mind...",
            "Whether the pleasure of making a daisy-chain..."
          ]
        }
      ],
      "sentence_count": 123,
      "word_count": 2184
    }
  ],
  "statistics": {
    "total_chapters": 12,
    "total_paragraphs": 450,
    "total_sentences": 1234,
    "total_words": 26358
  }
}
```

### Character Analysis (from OpenAI)
```json
{
  "characters": {
    "Alice": {
      "name": "Alice",
      "gender": "female",
      "role": "protagonist, young girl",
      "mentions": [
        {"start": 0, "end": 5, "text": "Alice"}
      ]
    }
  }
}
```

### Final Output: Transformed JSON
```json
{
  "metadata": {
    "transformation": {
      "type": "masculine",
      "model": "gpt-4o-mini",
      "timestamp": "2024-06-29T21:00:00Z"
    }
  },
  "chapters": [
    {
      "sentences": [
        "Alan was beginning to get very tired...",
        "He had peeped into the book..."
      ]
    }
  ],
  "transformation": {
    "changes": [
      "Changed 'Alice' to 'Alan'",
      "Changed 'She' to 'He' (15 instances)"
    ]
  }
}
```

## Key Components & Their Roles

### Core Processing:
1. **book_to_json.py** - Main entry point for text→JSON conversion
2. **book_parser/** - Modular parser with 100% success rate
3. **book_transform/** - Complete transformation system
   - **transform.py** - Main transformation orchestration
   - **character_analyzer.py** - Character identification
   - **llm_transform.py** - LLM integration
   - **chunking/** - Smart token-based chunking
4. **api_client.py** - Unified LLM client (OpenAI/Grok/MLX)

### Processing Commands:
1. **download**: Get books from Project Gutenberg
2. **process**: Convert text files to JSON format
3. **transform**: Apply gender transformation
4. **validate**: Check JSON accuracy
5. **list**: Show available books

### Transformation Types:
- **comprehensive**: Full gender transformation (default)
- **names_only**: Only transform character names
- **pronouns_only**: Only transform pronouns

## Parser Success Rates

- **Old Parser** (book_to_json_deprecated.py): 72/100 books
- **New Parser** (book_parser/): 100/100 books ✓

Successfully handles:
- Standard English chapters
- International formats (French, German)
- Plays and scripts
- Epistolary novels (letters)
- Story collections
- Complex nested structures

## Performance Optimizations

1. **Smart Pattern Matching**: Priority-based pattern system
2. **Caching**: All API responses cached for 24 hours
3. **Smart Chunking**: Model-adaptive chunk sizes
   - MLX: Handles up to 32K tokens
   - GPT-4o: Optimized for 8K chunks
   - Grok: Adjusted for model limits
4. **Paragraph Preservation**: Maintains text structure
5. **Local Processing**: MLX option for privacy/cost savings

## Error Recovery

1. **Chapter-level Recovery**: If one chapter fails, others continue
2. **Sentence Chunk Recovery**: Failed chunks can be retried
3. **Cache Persistence**: Successful transformations saved even if later chunks fail
4. **Pattern Fallback**: Uses generic patterns if specific ones don't match