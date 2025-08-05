# Workflow Guide

## Overview

The regender-xyz system provides a streamlined workflow for transforming gender representation in books. The `regender` command handles the entire pipeline automatically, including character analysis, transformation, and quality control.

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

#### all_male
Convert ALL characters to male gender with no exceptions.

```bash
python regender_book_cli.py regender book.txt --type all_male
```

**What happens:**
- ALL titles become 'Mr.' (never Mrs./Ms./Miss/Lady)
- ALL pronouns become 'he/him/his'
- Female names → male equivalents (Elizabeth→Elliot, Jane→John)
- Gendered terms (queen→king, mother→father)

#### all_female
Convert ALL characters to female gender with no exceptions.

```bash
python regender_book_cli.py regender book.txt --type all_female
```

**What happens:**
- ALL titles become 'Ms.' (never Mr.)
- ALL pronouns become 'she/her/hers'
- Male names → female equivalents (John→Jane, William→Willow)
- Gendered terms (king→queen, father→mother)

#### gender_swap
Swap each character's gender to its opposite.

```bash
python regender_book_cli.py regender book.txt --type gender_swap
```

**What happens:**
- Male characters → Female (he→she, Mr.→Ms., John→Jane)
- Female characters → Male (she→he, Ms.→Mr., Jane→John)
- Maintains consistency throughout the book


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
- Fails if character analysis cannot be completed

### 3. Transformation
- Processes book chapter by chapter
- Uses character context for accurate transformations
- Maintains narrative coherence

### 4. Quality Control
- Scans for missed transformations
- Uses AI to identify and fix errors
- Always runs 3 iterations for maximum accuracy

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
    python regender_book_cli.py regender "$json"
done
```


## Troubleshooting

### Character Analysis Fails
- Transformation stops (character analysis is mandatory)
- Solution: Check if book has clear character names and dialogue
- Solution: Try a different model or provider

### Low Quality Score
- Check transformation type matches book content
- Some books may have ambiguous gender references
- Consider using a more capable model

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