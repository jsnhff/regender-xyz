# Book Transform Module

This module handles AI-powered gender transformation of books with integrated quality control.

## Overview

The book transform module is the core transformation engine of regender-xyz. It takes parsed JSON books, applies gender transformations using AI, and includes quality control to ensure accuracy.

## Module Structure

```
book_transform/
├── transform.py           # Main transformation orchestration
├── unified_transform.py   # Complete pipeline with QC
├── llm_transform.py      # LLM prompt engineering
├── quality_control.py    # Post-transform validation
├── chunking/             # Smart text chunking
│   ├── smart_chunker.py # Token-aware chunking
│   ├── model_configs.py # Model-specific settings
│   └── token_utils.py   # Token counting utilities
└── validation/           # Transformation validation
    └── pronoun_validator.py
```

## Key Components

### 1. Unified Transformer (`unified_transform.py`)
The main entry point that orchestrates the complete pipeline:
- Character analysis (mandatory)
- Initial transformation
- Quality control iterations
- Validation and scoring
- Output generation

### 2. Transform Engine (`transform.py`)
Handles the core transformation logic:
- Chapter-by-chapter processing
- Smart chunking for API limits
- Progress tracking
- Character context integration

### 3. LLM Integration (`llm_transform.py`)
Manages AI prompts and transformations:
- Transform type definitions (all_male, all_female, gender_swap)
- Character-aware prompting
- Name mapping logic
- Consistency enforcement

### 4. Quality Control (`quality_control.py`)
Ensures transformation accuracy:
- Scans for missed transformations
- Context-aware error detection
- Iterative correction passes
- Quality scoring (0-100)

### 5. Smart Chunking (`chunking/`)
Optimizes API usage:
- Model-aware chunk sizing
- Token counting and limits
- Preserves paragraph boundaries
- Minimizes API calls

## Transformation Types

### all_male
- Converts ALL characters to male
- No exceptions allowed
- All pronouns → he/him/his
- All titles → Mr.

### all_female  
- Converts ALL characters to female
- No exceptions allowed
- All pronouns → she/her/hers
- All titles → Ms.

### gender_swap
- Swaps each character's gender
- Male → Female, Female → Male
- Maintains consistency throughout

## Quality Levels

### Fast
- No quality control
- Quickest processing
- Use for drafts/testing

### Standard (Default)
- 1 QC iteration
- Good balance of speed/quality
- Recommended for most uses

### High
- 3 QC iterations
- Mandatory character analysis
- Best for final versions

## Usage

### Python API

```python
from book_transform import UnifiedBookTransformer

# Create transformer
transformer = UnifiedBookTransformer(provider="openai")

# Transform with QC
transformed_book, report = transformer.transform_book_with_qc(
    book_data=book_json,
    transform_type="all_female",
    quality_level="standard"
)
```

### Command Line

```bash
# Use the unified regender command
python regender_book_cli.py regender book.txt --type all_female

# Or use individual transform command
python regender_book_cli.py transform book.json --type gender_swap
```

## Character Context

The transformer uses character analysis to maintain consistency:
- Tracks all character names and genders
- Ensures consistent transformations
- Handles name variants and nicknames
- Preserves relationships

## Model Support

Optimized for multiple providers:
- **OpenAI**: GPT-4o (128k), GPT-4o-mini
- **Anthropic**: Claude Opus 4, Claude 3.5 Sonnet
- **Grok**: Grok-4-latest (256k), Grok-3-latest (131k)

Each model has custom chunk sizing for optimal performance.

## Integration

Works with other modules:
- Receives parsed JSON from `book_parser`
- Uses character data from `book_characters`
- Outputs can be converted back to text using `book_parser` utilities