# Gender Transformation Pipeline

This document describes the complete transformation pipeline used by regender-xyz to transform gender representation in books while maintaining narrative coherence and text structure.

## Overview

The transformation pipeline consists of four main stages:

1. **Text Parsing** - Convert raw text to structured JSON
2. **Character Analysis** - Identify all characters and their genders
3. **Gender Transformation** - Transform text using LLM with character context
4. **Output Generation** - Create transformed JSON and text files

## Pipeline Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Raw Text      │     │ Character        │     │  Transformation │     │   Final Output  │
│   (.txt)        │ --> │ Analysis         │ --> │  Processing     │ --> │  (.json/.txt)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘     └─────────────────┘
        |                        |                        |                        |
   Parse to JSON           Identify chars          Apply gender             Save results
   Preserve structure      Extract genders         transformations          Maintain format
```

## Stage 1: Text Parsing

The parser converts any text format into a structured JSON representation:

### Features
- **100+ format support** - Handles standard chapters, international formats, plays, etc.
- **Paragraph preservation** - Maintains original text structure
- **Sentence splitting** - Intelligent handling of abbreviations (Mr., Mrs., etc.)
- **Metadata extraction** - Title, author, source information

### Process
```python
# Parse text to JSON
python regender_book_cli.py process --input books/texts --output books/json
```

### Output Structure
```json
{
  "metadata": {
    "title": "Book Title",
    "format_version": "2.0"
  },
  "chapters": [{
    "number": "1",
    "title": "Chapter Title",
    "paragraphs": [{
      "sentences": ["First sentence.", "Second sentence."]
    }]
  }]
}
```

## Stage 2: Character Analysis

Character analysis identifies all characters in the book and their genders using pure LLM analysis.

### Smart Chunking Strategy

For large books, the system uses strategic chunking:

1. **Beginning (25%)** - Character introductions
2. **Early-Middle Overlap** - Transition characters
3. **Middle (40-60%)** - Main plot characters
4. **Late-Middle Overlap** - Climax characters
5. **End (25%)** - Resolution characters

### Features
- **Pure LLM analysis** - No regex patterns, better accuracy
- **Anti-merging rules** - Prevents family member confusion
- **Name variant tracking** - Associates nicknames and titles
- **Position tracking** - Records where characters first appear

### Process
```python
# Analyze characters
python regender_book_cli.py analyze-characters books/json/book.json \
  --provider grok \
  --model grok-3-latest \
  --output books/json/book_characters.json
```

### Character Data Format
```json
{
  "metadata": {
    "analysis_model": "grok-3-latest",
    "character_count": 106
  },
  "characters": {
    "Harry Potter": {
      "name": "Harry Potter",
      "gender": "male",
      "role": "Main protagonist",
      "name_variants": ["Harry", "Potter"],
      "first_seen_in": "Beginning"
    }
  },
  "context": "Known characters:\n- Harry Potter: male\n..."
}
```

## Stage 3: Gender Transformation

The transformation stage processes the book using the character context.

### Transformation Process

1. **Load Character Context** - Pre-analyzed or automatic
2. **Smart Chunking** - Optimize for model context windows
3. **Numbered Sentences** - Maintain alignment
4. **LLM Processing** - Transform with character awareness
5. **Result Merging** - Combine transformed chunks

### Chunking Strategy

The system adapts chunk sizes based on the model:

| Model | Context Window | Chunk Size | Strategy |
|-------|----------------|------------|----------|
| GPT-4 | 8k | 50 sentences | Conservative |
| GPT-4o | 128k | 100 sentences | Balanced |
| Grok-3-latest | 131k | 100 sentences | Optimized |
| MLX Mistral-7B | 32k | 50 sentences | Memory-aware |

### Transformation Types

- **comprehensive** - Full gender transformation (default)
- **names_only** - Only transform character names
- **pronouns_only** - Only transform pronouns

### Process
```python
# Transform with pre-analyzed characters
python regender_book_cli.py transform books/json/book.json \
  --characters books/json/book_characters.json \
  --type comprehensive \
  --provider grok \
  --output books/output/book_transformed.json
```

## Stage 4: Output Generation

The final stage creates both JSON and text outputs.

### Features
- **Paragraph reconstruction** - Maintains original formatting
- **Change tracking** - Records all transformations
- **Validation** - Ensures output integrity

### Output Files

1. **Transformed JSON** - Complete structured data
2. **Transformed Text** - Human-readable book format
3. **Conversion Report** - Summary of changes

## Advanced Features

### Pre-analyzed Characters

Save time by analyzing characters once:

```python
# Step 1: Analyze and save
python regender_book_cli.py analyze-characters book.json \
  --output characters.json

# Step 2: Reuse for multiple transformations
python regender_book_cli.py transform book.json \
  --characters characters.json \
  --type comprehensive
```

### Batch Processing

Transform multiple books efficiently:

```python
# Process all JSON files
python regender_book_cli.py transform books/json/*.json \
  --type comprehensive \
  --batch
```

### Provider Selection

Choose the best provider for your needs:

- **Grok-3-latest** - Best for character analysis (131k context)
- **GPT-4o** - Best balance of quality and speed
- **GPT-4o-mini** - Most cost-effective
- **MLX** - Privacy and no API costs

## Transformation Quality

### Name Transformations

The system handles complex name transformations:
- Harry → Harriet
- James → Jamie
- William → Willow
- Preserves surnames and titles

### Pronoun Handling

Accurate pronoun transformation:
- he/him/his → she/her/hers
- Context-aware possessives
- Dialogue attribution

### Consistency

Character-aware transformation ensures:
- Same character always gets same transformation
- Family relationships preserved
- Narrative coherence maintained

## Performance Optimization

### Caching
- API responses cached for 24 hours
- Reduces redundant API calls
- Speeds up re-processing

### Parallel Processing
- Multiple chunks processed concurrently where possible
- Efficient use of API rate limits

### Memory Management
- Streaming for large files
- Chunked processing prevents memory overflow
- Progress tracking for long operations

## Error Handling

### Resilience Features
1. **Chapter-level recovery** - Failed chapters don't stop processing
2. **Chunk retry** - Automatic retry with exponential backoff
3. **Partial results** - Save successful transformations
4. **Detailed logging** - Track issues for debugging

### Common Issues and Solutions

**Character Merging**
- Problem: Family members merged (Harry and Lily Potter)
- Solution: Use grok-3-latest with updated prompts

**Sentence Splitting**
- Problem: Breaks at abbreviations
- Solution: Updated parser handles Mr., Mrs., etc.

**Memory Errors**
- Problem: MLX models run out of memory
- Solution: Automatic chunk size reduction

## Best Practices

1. **Parse First** - Always convert to JSON before transformation
2. **Analyze Characters** - Pre-analyze for better quality
3. **Save Intermediates** - Keep character analysis for reuse
4. **Use Appropriate Models** - Grok for analysis, GPT-4o for transformation
5. **Verify Output** - Check a few chapters manually

## Configuration

### Model Configuration (config/models.json)

```json
{
  "grok-3-latest": {
    "context_window": 131072,
    "tier": "flagship",
    "provider": "grok",
    "optimal_chunk_percentage": 0.85
  }
}
```

### Environment Variables

```bash
# API Keys
GROK_API_KEY=xai-...
OPENAI_API_KEY=sk-...

# Provider Selection
LLM_PROVIDER=grok

# Model Overrides
GROK_MODEL=grok-3-latest
OPENAI_MODEL=gpt-4o
```

## Monitoring and Debugging

### Verbose Mode

Use `--verbose` to see detailed processing information:
- Character analysis progress
- Chunk processing details
- API calls and responses
- Token usage estimates

### Log Files

Check logs for detailed debugging:
- `transformation.log` - Main processing log
- `api_calls.log` - API request/response details
- `errors.log` - Error tracking

## Future Enhancements

- **Streaming transformation** - Real-time processing
- **Multi-language support** - Beyond English
- **Custom transformation rules** - User-defined patterns
- **Interactive mode** - Review and adjust transformations
- **Parallel book processing** - Multiple books simultaneously