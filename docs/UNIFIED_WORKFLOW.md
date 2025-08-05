# Unified Workflow Documentation

## Overview

The regender-xyz system has been refactored to provide a unified, streamlined workflow for transforming gender representation in books. The new `regender` command handles the entire pipeline automatically, including character analysis, transformation, and quality control.

## Quick Start

### Simple Usage

Transform any book with a single command:

```bash
# Transform a text file
python regender_book_cli.py regender books/texts/pg1342-Pride_and_Prejudice.txt

# Transform a JSON file
python regender_book_cli.py regender books/json/pg1342-Pride_and_Prejudice_clean.json

# Specify output location
python regender_book_cli.py regender input.txt -o output/my_book_transformed
```

### Transformation Types

```bash
# All female (default: gender_swap)
python regender_book_cli.py regender book.txt --type all_female

# All male
python regender_book_cli.py regender book.txt --type all_male

# Gender swap (swaps all genders)
python regender_book_cli.py regender book.txt --type gender_swap
```

### Quality Levels

```bash
# Fast mode (no quality control)
python regender_book_cli.py regender book.txt --quality fast

# Standard mode (1 QC iteration) - DEFAULT
python regender_book_cli.py regender book.txt --quality standard

# High quality (3 QC iterations, mandatory character analysis)
python regender_book_cli.py regender book.txt --quality high
```

## The Unified Pipeline

The `regender` command automatically handles:

### 1. Input Processing
- Accepts both `.txt` and `.json` files
- Automatically parses text files to JSON if needed
- Validates input format

### 2. Character Analysis (Mandatory)
- Extracts all characters from the book
- Identifies character genders from context
- Builds character mapping for consistent transformation
- In high quality mode, fails if character analysis fails

### 3. Transformation
- Processes book chapter by chapter
- Uses character context for accurate transformations
- Maintains narrative coherence

### 4. Quality Control
- Scans for missed transformations
- Uses AI to identify and fix errors
- Runs multiple iterations based on quality level

### 5. Validation
- Calculates quality score (0-100)
- Reports remaining issues
- Validates character consistency

### 6. Output Generation
- Saves both JSON and text versions
- Includes transformation metadata
- Provides detailed reporting

## Example Output

```
════════════════════════════════════════════════════════════
Unified Regender Transformation
════════════════════════════════════════════════════════════
📖 Book: Pride and Prejudice
🔄 Transform: all_female
🎯 Quality: standard

Stage 1: Character Analysis
  ✓ Found 23 characters

Stage 2: Initial Transformation
  Chapter 1/61 ✓ (47 changes)
  Chapter 2/61 ✓ (32 changes)
  ...

Stage 3: Quality Control
  Quality Control Iteration 1/1
  Found 12 potential issues
  Applied 12 corrections

Stage 4: Validation
  Quality Score: 98/100
  Remaining Issues: 2

Stage 5: Saving Output
  ✓ JSON saved to: output/pg1342-Pride_and_Prejudice_all_female.json
  ✓ Text saved to: output/pg1342-Pride_and_Prejudice_all_female.txt

════════════════════════════════════════════════════════════
✓ Transformation Complete!
════════════════════════════════════════════════════════════
⏱️  Total time: 125.3s
📊 Quality score: 98/100
✏️  Total changes: 1,847
```

## Advanced Options

### Provider Selection

```bash
# Use Grok (default: OpenAI)
python regender_book_cli.py regender book.txt --provider grok

# Specify model
python regender_book_cli.py regender book.txt --model gpt-4o
```

### Batch Processing

For processing multiple books, use the traditional commands:

```bash
# Process all text files to JSON
python regender_book_cli.py process books/texts/

# Then transform with unified pipeline
for json in books/json/*.json; do
    python regender_book_cli.py regender "$json" --quality high
done
```

## Quality Level Details

### Fast Mode
- No quality control
- Character analysis if possible (not mandatory)
- Fastest processing
- Use for drafts or testing

### Standard Mode (Default)
- Character analysis required
- 1 iteration of quality control
- Good balance of speed and quality
- Recommended for most uses

### High Mode
- Mandatory character analysis (fails if not possible)
- 3 iterations of quality control
- Highest quality output
- Use for final/published versions

## Troubleshooting

### Character Analysis Fails
- In `fast` or `standard` mode: Continues with limited context
- In `high` mode: Transformation stops (character analysis is mandatory)
- Solution: Check if book has clear character names and dialogue

### Low Quality Score
- Run with `--quality high` for more iterations
- Check transformation type matches book content
- Some books may have ambiguous gender references

### Rate Limits
- The unified pipeline handles rate limits automatically
- For Grok with 16k token/minute limit, processing pauses as needed
- No manual intervention required

## Individual Commands (Still Available)

For debugging or custom workflows, individual commands remain available:

- `download` - Download from Project Gutenberg
- `process` - Convert text to JSON
- `analyze-characters` - Extract character data
- `transform` - Transform without QC
- `validate` - Check JSON integrity

But for normal use, just use `regender`!