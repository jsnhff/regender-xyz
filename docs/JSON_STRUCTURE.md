# JSON Book Structure Documentation

## Overview

The regender-xyz book parser converts text files into a structured JSON format that preserves the original formatting while making the content accessible for transformation and analysis.

## Current Structure (v2.0)

```json
{
  "metadata": {
    "title": "Book Title",
    "author": "Author Name",
    "date": "Publication Date",
    "source": "Project Gutenberg",
    "processing_note": "Parsed with modular book parser",
    "format_version": "2.0"
  },
  "chapters": [
    {
      "number": "1",
      "title": "Chapter Title",
      "type": "chapter",
      "paragraphs": [
        {
          "sentences": [
            "First sentence of the paragraph.",
            "Second sentence of the paragraph."
          ]
        },
        {
          "sentences": [
            "First sentence of next paragraph.",
            "Second sentence continues here."
          ]
        }
      ],
      "sentence_count": 4,
      "word_count": 25
    }
  ],
  "statistics": {
    "total_chapters": 10,
    "total_paragraphs": 500,
    "total_sentences": 2500,
    "total_words": 50000,
    "average_sentences_per_chapter": 250,
    "average_paragraphs_per_chapter": 50,
    "average_sentences_per_paragraph": 5,
    "average_words_per_sentence": 20
  }
}
```

## Key Features

### 1. Paragraph Preservation
- Each paragraph from the source text is preserved as a separate object
- Maintains the author's intended text structure
- Empty lines between paragraphs are respected

### 2. Sentence Handling
- Sentences within paragraphs are stored as an array
- Abbreviations (Mr., Mrs., Dr., etc.) are handled correctly
- Sentence boundaries are intelligently detected

### 3. Chapter Types
Supported chapter types include:
- `chapter` - Standard book chapters
- `act` - For plays
- `scene` - For dramatic works
- `letter` - For epistolary novels
- `prologue`/`epilogue` - Special sections
- `story` - For collections
- `livre` - French books

### 4. Statistics
Comprehensive statistics are calculated including:
- Total and average counts for chapters, paragraphs, sentences, and words
- Useful for analyzing book structure and planning transformations

## Example Usage

### Reading Sentences
```python
for chapter in book_data['chapters']:
    for paragraph in chapter['paragraphs']:
        for sentence in paragraph['sentences']:
            print(sentence)
```

### Recreating Text
```python
from book_parser import recreate_text_from_json

recreate_text_from_json('book.json', 'output.txt')
```

## Benefits

1. **Preservation of Intent**: Maintains the author's paragraph structure
2. **Better Context**: Transformations can consider paragraph boundaries
3. **Accurate Recreation**: Text can be recreated with proper formatting
4. **Flexibility**: Easy to work with at paragraph or sentence level
5. **Extensible**: Structure can be enhanced as needed

## Migration

Existing JSON files can be used as-is. To convert old files to the new structure:

```bash
# Reprocess the original text file
python regender_book_cli.py process --input books/texts --output books/json
```

The parser will automatically create files with the new paragraph-aware structure.