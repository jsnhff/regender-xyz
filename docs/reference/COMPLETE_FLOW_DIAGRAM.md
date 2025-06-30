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
│                        ENTRY POINTS                              │
├────────────────────────────┬─────────────────────────────────────┤
│    regender_cli.py         │      regender_json_cli.py           │
│  (Full text processing)    │   (JSON-based processing)           │
└────────────┬───────────────┴──────────────┬──────────────────────┘
             │                              │
             v                              v
┌────────────────────────────┐  ┌──────────────────────────────────┐
│   PREPROCESSING STAGE      │  │   JSON TRANSFORMATION STAGE      │
├────────────────────────────┤  ├──────────────────────────────────┤
│ book_to_json.py           │  │ json_transform.py                │
│  └─ process_book_to_json() │  │  ├─ transform_json_book()        │
│                           │  │  ├─ load character context       │
│ Uses book_parser/:        │  │  └─ process chapters             │
│  ├─ PatternRegistry       │  │                                  │
│  ├─ SectionDetector       │  │ For each chapter:                │
│  └─ BookParser API        │  │  ├─ chunk sentences (50 each)    │
│                           │  │  ├─ call OpenAI API              │
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
│                     OPENAI API CALLS                           │
├────────────────────────────────────────────────────────────────┤
│ 1. Character Analysis (analyze_characters.py)                  │
│    └─ GPT-4: Identify characters and their genders             │
│                                                                │
│ 2. Gender Transformation (gender_transform.py)                 │
│    └─ GPT-4/GPT-4o-mini: Transform pronouns                    │
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

### Intermediate: Clean JSON
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
      "sentences": [
        "Alice was beginning to get very tired...",
        "She had peeped into the book..."
      ],
      "sentence_count": 123,
      "word_count": 2184
    }
  ],
  "statistics": {
    "total_chapters": 12,
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
3. **json_transform.py** - JSON-based gender transformation
4. **gender_transform.py** - Core transformation logic & OpenAI integration
5. **utils.py** - API client, caching, error handling

### Processing Modes:
1. **Direct Text Mode**: Process entire text files at once
2. **JSON Mode**: Process pre-parsed JSON for better control
3. **Pipeline Mode**: Full analysis + transformation workflow

### Transformation Types:
- **Feminine**: he→she, Mr.→Ms., his→her
- **Masculine**: she→he, Ms.→Mr., her→his  
- **Neutral**: he/she→they, Mr./Ms.→Mx., his/her→their

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
3. **Chunking**: Process 50 sentences at a time
4. **Parallel Processing**: Chapters can be processed independently
5. **Model Selection**: Use gpt-4o-mini for bulk processing (faster/cheaper)

## Error Recovery

1. **Chapter-level Recovery**: If one chapter fails, others continue
2. **Sentence Chunk Recovery**: Failed chunks can be retried
3. **Cache Persistence**: Successful transformations saved even if later chunks fail
4. **Pattern Fallback**: Uses generic patterns if specific ones don't match