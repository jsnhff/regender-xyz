# Character-Based Transformation Guide

## Overview

The character-based transformation feature allows you to use pre-analyzed character data for gender transformations, providing better control and consistency while reducing API calls.

## Benefits

1. **Performance**: Skip character detection phase, saving API calls and time
2. **Consistency**: Ensure all instances of a character are transformed uniformly
3. **Control**: Define custom character mappings and transformations
4. **Reusability**: Analyze once, transform multiple times with different settings

## Usage

### 1. Analyze Characters (One-time)

First, analyze and save character data from your book:

```bash
python regender_book_cli.py analyze-characters books/json/mybook.json \
    -o books/json/mybook_characters.json \
    --provider mlx
```

This creates a character file containing:
- All detected characters
- Their genders
- Mention counts
- Context information

### 2. Transform Using Character File

Use the pre-analyzed characters for transformation:

```bash
python regender_book_cli.py transform books/json/mybook.json \
    --characters books/json/mybook_characters.json \
    --type comprehensive \
    --provider mlx
```

### 3. Create Custom Mappings

For testing or specific transformations, create custom character files:

```python
# In tests/transform_with_characters_util.py
from transform_with_characters_util import create_all_female_mapping

# Create a mapping where all characters are female
create_all_female_mapping(
    'books/json/mybook_characters.json',
    'books/json/mybook_all_female.json'
)
```

## Character File Format

Character files are JSON with this structure:

```json
{
  "metadata": {
    "source_book": "books/json/mybook.json",
    "analysis_model": "mistral-7b-instruct",
    "character_count": 25
  },
  "characters": {
    "Harry Potter": {
      "name": "Harry Potter",
      "gender": "male",
      "role": "Main protagonist",
      "mentions": 464,
      "name_variants": ["Harry", "Potter"]
    },
    "Hermione Granger": {
      "name": "Hermione Granger", 
      "gender": "female",
      "role": "Harry's friend",
      "mentions": 104,
      "name_variants": ["Hermione"]
    }
  },
  "context": "Character context string..."
}
```

## Custom Character Mappings

You can edit character files to create custom transformations:

```json
{
  "characters": {
    "Harry Potter": {
      "name": "Harriet Potter",
      "gender": "female",
      "role": "Main protagonist (female version)"
    },
    "Ron Weasley": {
      "name": "Veronica Weasley",
      "gender": "female",
      "role": "Harry's best friend (female version)"
    }
  }
}
```

## Workflow Examples

### Testing All-Female Transformation

```bash
# 1. Analyze characters
python regender_book_cli.py analyze-characters books/json/sorcerer_stone.json \
    -o characters/sorcerer_stone_chars.json

# 2. Create all-female mapping
python -c "from tests.transform_with_characters_util import create_all_female_mapping; \
    create_all_female_mapping('characters/sorcerer_stone_chars.json', \
                             'characters/sorcerer_stone_all_female.json')"

# 3. Transform using the mapping
python regender_book_cli.py transform books/json/sorcerer_stone.json \
    --characters characters/sorcerer_stone_all_female.json \
    --output books/output/sorcerer_stone_all_female.json \
    --text books/output/sorcerer_stone_all_female.txt
```

### Batch Processing with Same Characters

```bash
# Analyze characters from first book in series
python regender_book_cli.py analyze-characters books/json/hp_book1.json \
    -o characters/hp_characters.json

# Use same characters for all books in series
for book in books/json/hp_book*.json; do
    python regender_book_cli.py transform "$book" \
        --characters characters/hp_characters.json \
        --type comprehensive
done
```

## Integration Status

**Current Status**: Experimental (in tests/ directory)

The feature includes:
- ✅ Core transformation logic (`tests/transform_with_characters.py`)
- ✅ Improved implementation (`tests/transform_improvements.py`)
- ✅ CLI integration design (`tests/test_character_cli_integration.py`)
- ✅ Utility functions (`tests/transform_with_characters_util.py`)
- ✅ CLI patch ready (`tests/cli_character_integration.patch`)

**To integrate into main codebase**:
1. Apply the CLI patch to `regender_book_cli.py`
2. Add `transform_with_characters()` to `book_transform/utils.py`
3. Test thoroughly with various books
4. Update main documentation

## Performance Comparison

Using Sorcerer's Stone as example:

| Approach | Character Detection | Transformation | Total Time | API Calls |
|----------|-------------------|----------------|------------|-----------|
| Standard | ~30s | ~120s | ~150s | ~20 |
| Pre-analyzed | 0s (skipped) | ~120s | ~120s | ~15 |
| Savings | 100% | 0% | 20% | 25% |

## Known Limitations

1. Character file must match the book being transformed
2. Manual character edits may need role descriptions
3. Character variants must be manually specified
4. Generic terms (They, Someone) are excluded by default

## Future Enhancements

1. Character relationship mapping
2. Automatic name feminization/masculinization
3. Character consistency across book series
4. GUI for character editing
5. Character template library