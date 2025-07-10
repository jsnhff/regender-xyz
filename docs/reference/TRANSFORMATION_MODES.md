# Transformation Modes

This document describes the three transformation modes available in regender-xyz and how they work.

## Overview

The system supports three explicit transformation modes:

1. **all_male** - Convert ALL characters to male gender
2. **all_female** - Convert ALL characters to female gender
3. **gender_swap** - Swap each character's gender

## Mode Details

### all_male

Converts every character in the book to male gender with no exceptions.

**Transformations:**
- ALL titles become 'Mr.' (never Mrs./Ms./Miss/Lady)
- ALL pronouns become 'he/him/his'
- Female names to male equivalents (Elizabeth→Elliot, Jane→John, etc.)
- Gendered terms (queen→king, mother→father, etc.)

**Example command:**
```bash
python regender_book_cli.py transform books/json/book.json --type all_male
```

**Critical instructions sent to AI:**
- "EVERY character must be male. No exceptions."
- "ALL characters must be transformed, even if unnamed"
- "If you're unsure about a character's gender, make them male"

### all_female

Converts every character in the book to female gender with no exceptions.

**Transformations:**
- ALL titles become 'Ms.' (never Mr.)
- ALL pronouns become 'she/her/her'
- Male names to female equivalents (John→Jane, William→Willow, etc.)
- Gendered terms (king→queen, father→mother, etc.)

**Example command:**
```bash
python regender_book_cli.py transform books/json/book.json --type all_female
```

**Critical instructions sent to AI:**
- "EVERY character must be female. No exceptions."
- "ALL characters must be transformed, even if unnamed"
- "If you're unsure about a character's gender, make them female"

### gender_swap

Swaps each character's gender to its opposite.

**Transformations:**
- Male characters → Female (he→she, Mr.→Ms., John→Jane)
- Female characters → Male (she→he, Ms.→Mr., Jane→John)
- Neutral/unknown characters → Context-dependent decision

**Example command:**
```bash
python regender_book_cli.py transform books/json/book.json --type gender_swap
```

**Critical instructions sent to AI:**
- "Male characters become female, female characters become male"
- "Maintain consistency - if a character starts as male, they become female throughout"
- "Pay attention to character context from analysis"

## Character Name Mappings

The system uses explicit character name mappings to ensure consistent transformations:

### Common Female to Male Mappings:
- Elizabeth → Elliot
- Jane → John
- Mary → Mark
- Catherine/Kitty → Christopher/Kit
- Lydia → Louis
- Charlotte → Charles
- Caroline → Carl
- Georgiana → George
- Lady Catherine → Lord Christopher
- Mrs. Bennet → Mr. Bennet
- And many more...

### Common Male to Female Mappings:
- William → Willow
- Charles → Charlotte
- George → Georgia
- Edward → Edith
- Thomas → Thomasina
- Richard → Rachel
- Robert → Roberta
- James → Jamie
- John → Jane
- Mr. Collins → Ms. Collins
- And many more...

## Quality Control

After transformation, you can use the review loop to ensure 100% accuracy:

```bash
# Run quality control on transformed text
python run_review_loop.py books/output/book_all_male.txt all_male
```

The review loop will:
1. Scan for any remaining gendered language that doesn't match the mode
2. Use AI to find context-aware issues
3. Apply iterative learning passes until 100% transformation achieved
4. Save a quality-controlled version with "_qc" suffix

## Implementation Details

The transformation modes are defined in `book_transform/llm_transform.py`:

```python
TRANSFORM_TYPES = {
    "all_male": {
        "name": "All Male",
        "description": "Convert ALL characters to male gender - no exceptions",
        "changes": [
            "ALL titles become 'Mr.' (never Mrs./Ms./Miss/Lady)", 
            "ALL pronouns become 'he/him/his'",
            "Female names to male equivalents"
        ]
    },
    # Similar for all_female and gender_swap
}
```

## Best Practices

1. **Use character analysis**: Always let the system analyze characters first for better context
2. **Choose the right mode**: Be explicit about your transformation goal
3. **Run quality control**: Use the review loop for important transformations
4. **Check the output**: Always review a sample of the transformed text
5. **Use appropriate models**: Grok-3-latest or GPT-4o for best results with large books

## Common Issues and Solutions

### Mixed genders in output
- **Cause**: Using vague or incorrect transformation type
- **Solution**: Use explicit modes (all_male, all_female, gender_swap)

### Inconsistent character names
- **Cause**: Missing character context
- **Solution**: Let the system analyze characters first

### Some pronouns not transformed
- **Cause**: Complex sentence structures or ambiguous references
- **Solution**: Run the review loop for quality control

## API-Specific Notes

### Grok
- Supports 131k context window
- Best for large books
- Use `--provider grok --model grok-3-latest`

### OpenAI
- GPT-4o has 128k context window
- Best quality transformations
- Use `--provider openai --model gpt-4o`

### MLX (Local)
- No API costs
- Smaller context window (32k)
- Use `--provider mlx`