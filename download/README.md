# Download Module

Utilities for downloading books from online sources (currently Project Gutenberg).

## Overview

This package provides functionality for downloading books from Project Gutenberg's website. It handles:
- Parsing the Project Gutenberg top books page
- Finding download URLs for plain text versions
- Managing downloads with rate limiting
- Organizing files with clean naming

## Structure

```
download/
├── __init__.py        # Package initialization
└── download.py        # Download books from online sources
```

## Usage

### Command Line Interface

The main interface is through `regender_book_cli.py`:

```bash
# Download top 100 books
python regender_book_cli.py download

# Download specific number of books
python regender_book_cli.py download --count 50 --output book_texts
```

### Python API

```python
from download import GutenbergDownloader

# Create downloader
downloader = GutenbergDownloader(output_dir="book_texts")

# Download top books
stats = downloader.download_top_books(limit=100)

# Download specific book
downloader.download_book(book_id="1342", title="Pride and Prejudice")
```

## Components

### download.py

Downloads books directly from Project Gutenberg to a specified directory.

**Key features:**
- Downloads plain text versions of books
- Automatic URL pattern detection (tries multiple URL formats)
- Respectful rate limiting (1 second between downloads)
- Progress tracking and error handling
- SSL certificate handling for development

**Classes:**
- `GutenbergDownloader`: Main download class

**Methods:**
- `fetch_top_books_list(limit)`: Fetch list of top books from Gutenberg
- `download_book(book_id, title)`: Download a single book
- `download_top_books(limit)`: Download top N books
- `get_text_url(book_id)`: Generate download URL for a book

## Output Format

Downloaded files are saved as `pg{ID}-{Title}.txt` where:
- `{ID}` is the Project Gutenberg book ID
- `{Title}` is a sanitized version of the book title

Example: `pg1342-Pride_and_Prejudice.txt`

## Dependencies

- Python 3.6+
- beautifulsoup4 (for HTML parsing)
- requests (optional, falls back to urllib)

## Integration

This package is designed to work with the parser service for processing downloaded books:

```python
# Download books
from download import GutenbergDownloader
downloader = GutenbergDownloader()
downloader.download_top_books(100)

# Process books (using the CLI)
# python regender_cli.py book_texts/book.txt all_female
```

## Error Handling

- Failed downloads are logged and skipped
- Retries with different URL patterns if primary URL fails
- Continues processing even if some books fail to download

## Rate Limiting

The downloader includes a 1-second delay between downloads to be respectful to Project Gutenberg's servers.

## Notes

This package focuses solely on downloading functionality. For book parsing, validation, and processing, use the main CLI.