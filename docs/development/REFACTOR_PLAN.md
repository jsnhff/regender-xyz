# Book Processing System Refactoring Plan

## Overview
Separate book parsing/formatting from AI transformation logic for cleaner architecture.

## Current Issues
1. `json_transform.py` contains both book-specific logic and AI transformation logic
2. No clear separation between book processing and gender transformation
3. Mixed responsibilities across modules

## Proposed Architecture

### 1. book_parser Package (Pure Book Processing)
**Purpose**: Convert any text format to standardized JSON, no AI dependencies

```
book_parser/
├── __init__.py
├── parser.py              # Main parser class
├── patterns/              # Chapter detection patterns
├── detectors/             # Format detection
├── utils/
│   ├── validator.py       # Validate JSON against source
│   ├── batch_processor.py # Process multiple books
│   └── text_utils.py      # Text manipulation utilities
└── formatters/
    ├── json_formatter.py  # JSON output formatting
    └── text_formatter.py  # Text recreation from JSON
```

**Responsibilities**:
- Text file → JSON conversion
- Format detection and normalization
- Chapter/section detection and numbering
- Sentence splitting and cleanup
- JSON validation
- Text recreation from JSON

### 2. gender_transform Package (AI Transformation)
**Purpose**: Transform gender in JSON books using AI

```
gender_transform/
├── __init__.py
├── transform.py           # Main transformation logic
├── character_analyzer.py  # Character analysis
├── chunking/
│   ├── smart_chunker.py   # Token-aware chunking
│   └── token_utils.py     # Token estimation
└── providers/
    ├── base.py            # Base AI provider
    ├── openai_provider.py # OpenAI implementation
    └── grok_provider.py   # Grok implementation
```

**Responsibilities**:
- Character analysis from JSON book
- Gender transformation via AI
- Smart chunking for API limits
- Transformation tracking
- Multiple AI provider support

## Migration Steps

### Phase 1: Clean up book_parser
1. Move `recreate_text_from_json` to `book_parser/formatters/text_formatter.py`
2. Create `book_parser/formatters/json_formatter.py` for JSON output logic
3. Ensure book_parser has NO dependencies on AI/transformation code

### Phase 2: Consolidate transformation logic
1. Move character analysis from `json_transform.py` to `gender_transform/character_analyzer.py`
2. Move transformation logic to `gender_transform/transform.py`
3. Move chunking logic to `gender_transform/chunking/`
4. Update imports in `regender_book_cli.py`

### Phase 3: Clean up interfaces
1. book_parser exports:
   ```python
   from book_parser import (
       BookParser,
       parse_file,
       parse_directory,
       validate_json,
       recreate_text
   )
   ```

2. gender_transform exports:
   ```python
   from gender_transform import (
       transform_book,
       analyze_characters,
       GenderTransformer
   )
   ```

## Benefits
1. **Clear separation of concerns**: Book processing vs AI transformation
2. **Reusability**: book_parser can be used for any text processing task
3. **Maintainability**: Changes to AI logic don't affect book parsing
4. **Testability**: Can test book parsing without AI dependencies
5. **Flexibility**: Easy to add new book formats or AI providers

## API Examples

### Book Processing
```python
from book_parser import BookParser

# Parse a book
parser = BookParser()
book_json = parser.parse_file("pride_and_prejudice.txt")
parser.save_json(book_json, "pride_and_prejudice.json")

# Validate JSON
from book_parser import validate_json
is_valid = validate_json("pride_and_prejudice.json", "pride_and_prejudice.txt")

# Recreate text
from book_parser import recreate_text
text = recreate_text("pride_and_prejudice.json")
```

### Gender Transformation
```python
from gender_transform import GenderTransformer
from book_parser import load_json

# Load parsed book
book_data = load_json("pride_and_prejudice.json")

# Transform gender
transformer = GenderTransformer(provider="openai", model="gpt-4o-mini")
transformed_book = transformer.transform_book(
    book_data,
    transform_type="comprehensive"
)

# Save transformed book
save_json(transformed_book, "pride_and_prejudice_transformed.json")
```

## Implementation Priority
1. **High**: Move `recreate_text_from_json` to book_parser
2. **High**: Create gender_transform package structure
3. **Medium**: Migrate transformation logic from json_transform.py
4. **Medium**: Update regender_book_cli.py imports
5. **Low**: Add new features (more formats, providers)

## Files to Update/Move
1. `json_transform.py` → Split into gender_transform package
2. `analyze_characters.py` → Move to gender_transform/character_analyzer.py
3. `model_configs.py` → Move to gender_transform/chunking/
4. `token_utils.py` → Move to gender_transform/chunking/
5. `api_client.py` → Keep as is (used by multiple modules)
6. `regender_book_cli.py` → Update imports

## Testing Strategy
1. Ensure book_parser tests work without AI dependencies
2. Create separate tests for gender_transform with mocked AI responses
3. Integration tests for full pipeline