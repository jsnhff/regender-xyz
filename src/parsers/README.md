# Parser Architecture

The modular parser system for processing Project Gutenberg texts into structured JSON format.

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RAW GUTENBERG TEXT                          │
│  (Headers, footers, metadata, TOC, actual content all mixed)        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      gutenberg.py (Cleaner)                         │
│  • Removes headers/footers using line-based detection               │
│  • Extracts metadata (title, author, date, etc.)                    │
│  • Identifies and preserves Table of Contents                       │
│  • Returns clean text + metadata                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      detector.py (Format Detector)                  │
│  • Analyzes text patterns (no regex, just string operations)        │
│  • Detects 6 formats: Standard, Play, Multi-part,                   │
│    Poetry, Epistolary, Mixed                                        │
│  • Returns format type + confidence score (0-100%)                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
                    ┌──────────┴──────────┐
                    │   Format Router     │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼                             ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│   hierarchy.py            │   │   play.py                 │
│   (Standard/Multi-part)   │   │   (Theatrical Plays)      │
├───────────────────────────┤   ├───────────────────────────┤
│ • Builds tree structure   │   │ • Parses acts/scenes      │
│ • Handles Volume→Chapter  │   │ • Extracts dialogue       │
│ • Handles Part→Chapter    │   │ • Preserves stage dirs    │
│ • Skips duplicate TOC     │   │ • Character names         │
└───────────────┬───────────┘   └───────────────┬───────────┘
                │                               │
                └────────────┬──────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      parser.py (Integration)                        │
│  • Orchestrates all components                                      │
│  • Routes to appropriate parser based on format                     │
│  • Converts to unified chapter/paragraph structure                  │
│  • Returns ParsedBook object                                        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        STRUCTURED JSON OUTPUT                       │
│  {                                                                  │
│    "title": "Book Title",                                           │
│    "author": "Author Name",                                         │
│    "chapters": [                                                    │
│      {                                                              │
│        "number": 1,                                                 │
│        "title": "Chapter One",                                      │
│        "paragraphs": ["...", "..."]                                 │
│      }                                                              │
│    ]                                                                │
│  }                                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔧 Components

### Core Modules

1. **gutenberg.py** - Project Gutenberg text cleaner
   - Line-based processing (no regex for reliability)
   - Smart header/footer detection
   - Metadata extraction from various formats
   - TOC preservation

2. **detector.py** - Format detection engine
   - Pattern matching using string operations
   - Confidence scoring algorithm
   - Multi-format detection
   - Provides parsing recommendations

3. **hierarchy.py** - Multi-level structure builder
   - Tree-based hierarchy (Volume→Book→Chapter)
   - TOC duplicate detection and skipping
   - Section class with recursive structure
   - Flat conversion for compatibility

4. **play.py** - Theatrical play parser
   - Act and scene structure
   - Character dialogue extraction
   - Stage direction preservation
   - Dramatis personae handling

5. **parser.py** - Integration layer
   - Component orchestration
   - Format-based routing
   - Unified output format
   - ParsedBook data structure

## 🎯 Design Principles

1. **Line-based processing** - Avoid regex except where absolutely necessary
2. **Modular architecture** - Each component has single responsibility
3. **Graceful degradation** - Works with malformed/unusual texts
4. **Format agnostic** - Extensible to new formats
5. **Preserve content** - No loss of original text information

## 📝 Usage Example

```python
from src.parsers.parser import IntegratedParser

# Initialize parser
parser = IntegratedParser()

# Parse a book
with open("book.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

result = parser.parse(raw_text)

# Access structured data
print(f"Title: {result.title}")
print(f"Author: {result.author}")
print(f"Format: {result.format.value} ({result.format_confidence}%)")
print(f"Chapters: {len(result.chapters)}")

# Work with chapters
for chapter in result.chapters:
    print(f"Chapter {chapter['number']}: {chapter['title']}")
    print(f"  Paragraphs: {len(chapter['paragraphs'])}")
```

## 🧪 Test Coverage

Successfully tested on 20+ diverse books:
- **Novels**: Dracula, Emma, Ulysses
- **Plays**: Romeo & Juliet, Doll's House  
- **Multi-volume**: Count of Monte Cristo (5 volumes)
- **Poetry**: Beowulf
- **Reference**: Encyclopedia
- **Mixed formats**: Various combinations

**Success rate**: 100% (no crashes)
**Accuracy**: ~85% correct format detection

## 🔄 Data Flow

1. **Input**: Raw text file (possibly with Gutenberg headers/footers)
2. **Cleaning**: Remove boilerplate, extract metadata
3. **Detection**: Identify book format and structure
4. **Parsing**: Route to appropriate parser
5. **Building**: Create hierarchical structure
6. **Conversion**: Transform to unified format
7. **Output**: Structured JSON-compatible object

## 🚀 Future Improvements

- [ ] Poetry format specialized parser
- [ ] Epistolary (letters) format parser
- [ ] Better handling of mixed formats
- [ ] Improved author extraction patterns
- [ ] Support for non-English texts
- [ ] Performance optimization for large texts