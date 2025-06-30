# Gutenberg Utilities

A collection of tools for downloading, processing, and analyzing Project Gutenberg books.

## Quick Start

The easiest way to use these utilities is through the main `gutenberg_cli.py` CLI:

```bash
# Download top 100 books and process them
python gutenberg_cli.py pipeline

# Download only (top 50 books)
python gutenberg_cli.py download --count 50

# Process already downloaded books
python gutenberg_cli.py process

# List downloaded books
python gutenberg_cli.py list
```

## Components

### 1. **download_gutenberg_books.py**
Downloads books from Project Gutenberg's top books list.

```python
from gutenberg_utils import GutenbergDownloader

downloader = GutenbergDownloader(output_dir="books", max_books=100)
stats = downloader.download_top_books()
```

Features:
- Downloads from Project Gutenberg's top 100 list
- Automatically finds plain text versions
- Handles multiple URL patterns
- Respects server rate limits
- Creates organized folder structure

### 2. **collect_gutenberg_texts.py**
Collects downloaded text files into a single directory.

```python
from gutenberg_utils import collect_texts

stats = collect_texts(
    input_dir="gutenberg_books",
    output_dir="gutenberg_texts"
)
```

Features:
- Finds all .txt files in downloaded folders
- Renames files with book titles for clarity
- Handles filename sanitization
- Provides listing functionality

### 3. **process_all_gutenberg.py**
Batch converts text files to clean JSON format using the book parser.

```python
from gutenberg_utils import process_all_books

stats = process_all_books(
    input_dir="gutenberg_texts",
    output_dir="gutenberg_json"
)
```

Features:
- Processes all books with the advanced parser
- Handles 100+ book formats
- Tracks statistics and timing
- Provides detailed progress updates

### 4. **analyze_book_formats.py**
Analyzes book formats to understand patterns and edge cases.

```python
from gutenberg_utils import BookFormatAnalyzer

analyzer = BookFormatAnalyzer()
results = analyzer.analyze_all_books("gutenberg_texts")
analyzer.save_analysis("analysis.json")
```

Features:
- Identifies chapter patterns
- Finds special sections
- Collects format statistics
- Helps improve parser patterns

### 5. **conversion_summary.py**
Generates summary reports of processed books.

```bash
python gutenberg_utils/conversion_summary.py
```

Features:
- Analyzes all JSON files
- Identifies books without chapters
- Shows processing statistics
- Lists longest books

## Directory Structure

After running the pipeline, you'll have:

```
regender-xyz/
├── gutenberg_books/     # Original downloads (organized by book)
│   ├── pg1342_pride_and_prejudice/
│   ├── pg11_alices_adventures_in_wonderland/
│   └── ...
├── gutenberg_texts/     # Collected text files (flat structure)
│   ├── pg1342-Pride_and_Prejudice.txt
│   ├── pg11-Alice's_Adventures_in_Wonderland.txt
│   └── ...
└── gutenberg_json/      # Processed JSON files
    ├── pg1342-Pride_and_Prejudice_clean.json
    ├── pg11-Alice's_Adventures_in_Wonderland_clean.json
    └── ...
```

## Requirements

- Python 3.9+
- BeautifulSoup4 (optional, for better HTML parsing)
  ```bash
  pip install beautifulsoup4
  ```

## Usage Examples

### Download Specific Number of Books
```bash
python gutenberg_cli.py download --count 25
```

### Process Books in Custom Directory
```bash
python gutenberg_cli.py process --input my_texts --output my_json
```

### Analyze Book Formats
```python
from gutenberg_utils import BookFormatAnalyzer

analyzer = BookFormatAnalyzer()
results = analyzer.analyze_all_books("gutenberg_texts")

# Find books with specific patterns
french_books = [b for b in results if 'Chapitre' in b.get('patterns', [])]
plays = [b for b in results if b.get('has_acts', False)]
```

### Get Download Statistics
```python
from gutenberg_utils import GutenbergDownloader

downloader = GutenbergDownloader(max_books=10)
stats = downloader.download_top_books()

print(f"Downloaded: {stats['successful']} books")
print(f"Total size: {stats['total_size']}")
print(f"Failed: {stats['failed']} books")
```

## Features

- **Automatic Retry**: Failed downloads are retried with backoff
- **Progress Tracking**: Visual progress for all operations  
- **Format Detection**: Automatically finds text file URLs
- **Rate Limiting**: Respects Gutenberg's servers
- **Error Handling**: Continues on failures, reports at end
- **Statistics**: Detailed stats for all operations

## Tips

1. **First Time Setup**: Use `python gutenberg_cli.py pipeline` to get everything
2. **Reprocessing**: Use the main regender CLI to reprocess individual books
3. **Custom Books**: Add your own .txt files to `gutenberg_texts/` to process them
4. **Memory Usage**: Process in batches if working with 1000+ books

## Integration with Regender

After downloading and processing books, use them with regender:

```bash
# Transform a specific book
python regender_json_cli.py gutenberg_json/pg1342-Pride_and_Prejudice_clean.json -t feminine

# Batch transform multiple books
for book in gutenberg_json/*.json; do
    python regender_json_cli.py "$book" -t masculine -o "output/$(basename "$book")"
done
```

## Troubleshooting

- **No BeautifulSoup**: Install with `pip install beautifulsoup4` for better parsing
- **Download Failures**: Some books may not have text versions available
- **Parsing Errors**: Check `gutenberg_json/` for books with 0 chapters
- **Rate Limits**: Increase delay if getting blocked