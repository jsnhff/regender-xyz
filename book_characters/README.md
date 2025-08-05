# Book Characters Module

This module handles all character analysis and extraction functionality for the regender-xyz project. It provides a preprocessing phase where characters are identified, analyzed, and a reference is built for use during gender transformation.

## Overview

The character analysis phase is crucial for accurate gender transformation. By identifying characters and their current genders before transformation, the system can:
- Maintain consistency across the entire book
- Handle character-specific transformations
- Preserve narrative coherence
- Avoid transforming non-character references

**Important**: This module now uses only flagship-quality prompts for ALL models. We prioritize accuracy over cost because errors in character identification cascade through the entire book transformation and waste significant human proofreading time.

## Module Structure

```
book_characters/
├── __init__.py               # Module exports
├── analyzer.py               # Main character analysis with LLM
├── prompts.py               # Flagship-quality character analysis prompts
├── smart_chunked_analyzer.py # Smart chunking for comprehensive coverage
├── rate_limited_analyzer.py  # Rate-limited analysis for API constraints
├── api_chunked_analyzer.py   # Chunked processing for API providers
├── context.py                # Character context creation for transformations
├── loader.py                 # Load pre-analyzed character data
└── utils.py                  # Utility functions
```

## Key Features

### 1. Flagship-Quality Character Detection

The module uses only the highest quality prompting approach for character identification:

**Character Analysis** (analyzer.py)
- Uses flagship-quality prompts for ALL models (no tier system)
- Comprehensive character extraction with zero tolerance for errors
- Extracts gender from pronouns, titles, and context
- Identifies character roles and relationships
- Handles name variations and aliases
- Supports 100+ characters per book
- Family members are ALWAYS kept as separate characters

### 2. Smart Chunking Strategy

For large context models like Grok-3-latest (131k tokens):

**Strategic Analysis** (smart_chunked_analyzer.py)
- Analyzes beginning (25%) - character introductions
- Analyzes middle (40-60%) - main plot development
- Analyzes end (25%) - resolution
- Includes overlap zones to catch boundary characters
- Ensures comprehensive character coverage

### 3. Rate-Limited Analysis

For APIs with strict rate limits (e.g., Grok-4-latest with 16k tokens/minute):

**Intelligent Rate Limiting** (rate_limited_analyzer.py)
- Tracks token usage in real-time
- Automatically pauses when approaching limits
- Resumes processing after rate window resets
- Optimizes chunk sizes to maximize throughput
- Provides progress tracking and token usage stats

### 4. Character Context Generation

Creates a concise character reference for the transformation phase:
```
Known characters:
- Harry Potter: male
- Hermione Granger: female
- Ron Weasley: male
- Albus Dumbledore: male
- Lily Potter: female
```

## Usage Examples

### Basic Character Analysis

```python
from book_characters import analyze_book_characters

# Analyze a book
characters, context = analyze_book_characters(
    book_data,
    model="grok-3-latest",  # Recommended for large books
    provider="grok",        # Supports openai, grok, mlx
    verbose=True
)

# Results
print(f"Found {len(characters)} characters")
print(context)
```

### Rate-Limited Analysis for Large Books

```python
from book_characters import analyze_book_with_rate_limits

# Analyze with rate limiting (essential for grok-4-latest)
characters = analyze_book_with_rate_limits(
    book_file="books/json/large_book.json",
    output_file="books/json/large_book_characters.json",
    model="grok-4-latest",
    provider="grok",
    tokens_per_minute=16000,  # Grok's limit
    verbose=True
)

# The analyzer will:
# - Track token usage per chunk
# - Pause when approaching the limit
# - Resume automatically after rate window resets
# - Save results with analysis history
```

### Using Pre-analyzed Characters

```python
from book_characters import load_character_file, create_character_context

# Load saved character analysis
characters = load_character_file("characters.json")
context = create_character_context(characters)

# Use for transformation
from book_transform.utils import transform_with_characters
transformed = transform_with_characters(
    book_data,
    character_file="characters.json",
    transform_type="comprehensive",
    model="grok-3-latest",
    provider="grok"
)
```

### Export Character Data

```python
from book_characters import save_character_analysis

# Save as JSON
save_character_analysis(
    characters, 
    "output/characters.json",
    book_metadata={
        "title": "Harry Potter and the Sorcerer's Stone",
        "author": "J.K. Rowling"
    }
)
```

## CLI Integration

The module integrates seamlessly with the main CLI:

```bash
# Analyze characters in a book (uses flagship-quality prompts)
python regender_book_cli.py analyze-characters book.json \
    --output characters.json \
    --provider grok \
    --model grok-4-latest

# For large books with rate limits (auto-enabled for grok-4-latest)
python regender_book_cli.py analyze-characters large_book.json \
    --output characters.json \
    --provider grok \
    --model grok-4-latest \
    --rate-limited \
    --tokens-per-minute 16000

# Transform using pre-analyzed characters (much faster)
python regender_book_cli.py transform book.json \
    --characters characters.json \
    --type comprehensive \
    --provider grok \
    --output transformed.json \
    --text transformed.txt
```

## Character Analysis Results

Example from Harry Potter analysis with Grok:
- **Total characters found**: 106
- **Gender distribution**: 61 male, 39 female, 6 unknown
- **Processing time**: ~5-10 minutes
- **Accuracy**: Correctly identifies all major and minor characters

## Smart Chunking Details

The smart chunking strategy ensures complete book coverage:

1. **Beginning Analysis** (25%)
   - Captures character introductions
   - Establishes main cast

2. **Early-Middle Transition**
   - Catches characters introduced after setup
   - Overlap prevents missing boundary characters

3. **Middle Analysis** (40-60%)
   - Main plot characters
   - Supporting cast

4. **Late-Middle Transition**
   - Characters appearing in climax setup

5. **End Analysis** (25%)
   - Resolution characters
   - Late introductions

## Best Practices

1. **Use Top-Tier Models**: Always use GPT-4o, Grok-4-latest, or similar flagship models
2. **Save Character Data**: Analyze once, use multiple times
3. **Verify Character Count**: 100+ characters indicates comprehensive analysis
4. **Use Pre-analyzed Characters**: Faster transformation, consistent results
5. **Check Gender Distribution**: Ensure reasonable male/female balance
6. **Quality Over Cost**: The extra cost of flagship models is insignificant compared to human proofreading time

## Technical Details

### Character Merging Prevention

The system includes rules to prevent incorrect character merging:
- Family members are kept separate (Harry Potter ≠ Lily Potter)
- Title variations are merged correctly (Mr. Potter = James Potter)
- Nicknames are associated properly

### Gender Detection

Gender is determined through:
1. Pronouns (he/him/his vs she/her/hers)
2. Titles (Mr./Mrs./Ms./Sir/Lady)
3. Context clues from narrative
4. Character relationships

### Output Format

```json
{
  "metadata": {
    "source_book": "books/json/book.json",
    "analysis_model": "grok-3-latest",
    "analysis_provider": "grok",
    "character_count": 106
  },
  "characters": {
    "Harry Potter": {
      "name": "Harry Potter",
      "gender": "male",
      "role": "Main protagonist, the boy who lived",
      "name_variants": ["Harry", "Potter"],
      "first_seen_in": "Beginning (Introduction)"
    }
  },
  "context": "Known characters:\n- Harry Potter: male\n..."
}
```

## Performance Optimization

- **Chunked Processing**: Handles books of any size
- **Strategic Sampling**: Analyzes key sections for complete coverage
- **Context Efficiency**: Uses 85% of available context for Grok
- **Parallel Analysis**: Multiple chunks can be processed concurrently

## Recent Improvements

- Removed regex-based scanning for pure LLM analysis
- Added smart chunking for comprehensive coverage
- Improved prompt engineering to prevent character merging
- Enhanced support for large books (tested on 400k+ character texts)
- Better handling of complex family relationships

## Future Enhancements

- Character relationship graphs
- Emotion and sentiment tracking
- Character arc analysis
- Multi-language support
- Interactive character mapping tools