# Books Directory Structure

This directory contains all book-related files for the ReGender-XYZ project.

## Directory Structure

```
books/
├── texts/      # Original text files (downloaded or imported)
├── json/       # Parsed JSON representations
└── output/     # Transformed books (gender-swapped versions)
```

## Workflow

1. **Download/Import** → `books/texts/`
   - Downloaded from Project Gutenberg
   - Or manually placed text files

2. **Parse** → `books/json/`
   - Converts text to structured JSON
   - Identifies chapters and sentences
   - Preserves formatting and structure

3. **Transform** → `books/output/`
   - Applies gender transformations
   - Maintains original structure
   - Can output as JSON or text

## Examples

```bash
# Download books
python regender_book_cli.py download --count 10

# Process to JSON
python regender_book_cli.py process

# Transform with API
python regender_book_cli.py transform books/json/book.json --provider grok
```