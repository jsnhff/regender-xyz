# Book Parser Refactor Plan

## Current Issues to Fix

### 1. Import Dependencies
- `batch_processor.py` imports from `book_to_json` (external dependency)
- Need to refactor to use internal `BookParser` class

### 2. Path Corrections
- Update import paths in `batch_processor.py` and `validator.py` for new utils location
- Fix sys.path manipulations

### 3. Main __init__.py Updates
- Update imports to reference utils subdirectory:
  ```python
  from .utils.batch_processor import process_all_books, generate_summary_report
  from .utils.validator import BookValidator
  ```

## Refactor Steps

### Step 1: Fix batch_processor.py imports
```python
# Change from:
from book_to_json import process_book_to_json

# To:
from ..parser import BookParser
```

### Step 2: Refactor process_book_to_json usage
Replace external function call with internal BookParser:
```python
# Instead of:
book_data = process_book_to_json(str(txt_file), str(output_file), verbose=False)

# Use:
parser = BookParser()
book_data = parser.parse_file(str(txt_file))
# Save to JSON
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(book_data, f, indent=2, ensure_ascii=False)
```

### Step 3: Update gutenberg_cli.py imports
Change from current mixed imports to clean separation:
```python
from gutenberg_utils import GutenbergDownloader
from book_parser import BookValidator, process_all_books
```

### Step 4: Final Directory Structure
```
book_parser/
├── __init__.py
├── parser.py
├── patterns/
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   ├── standard.py
│   ├── international.py
│   └── plays.py
├── detectors/
│   ├── __init__.py
│   └── section_detector.py
└── utils/
    ├── __init__.py
    ├── batch_processor.py
    └── validator.py
```

## Testing After Refactor

1. Test imports:
   ```python
   from book_parser import BookParser, BookValidator, process_all_books
   ```

2. Test batch processing:
   ```bash
   python -m book_parser.utils.batch_processor --input gutenberg_texts --output test_json
   ```

3. Test validation:
   ```bash
   python -m book_parser.utils.validator --texts-dir gutenberg_texts --json-dir test_json
   ```

## Future Improvements (Lower Priority)

1. Add `extractors/` module for metadata extraction
2. Add `formatters/` module for output formatting
3. Add unit tests in `tests/` subdirectory
4. Extract configuration to `config.py`

## Files to Update

1. `/book_parser/__init__.py` - Update imports
2. `/book_parser/utils/batch_processor.py` - Fix external dependency
3. `/book_parser/utils/validator.py` - Update import paths
4. `/gutenberg_cli.py` - Update book_parser imports

## Commands to Run After Compact

```bash
# 1. Fix the batch_processor import issue
cd /Users/williambarnes/Development/regender-xyz

# 2. Update __init__.py
# Edit book_parser/__init__.py to use utils.module imports

# 3. Test the refactored structure
python -c "from book_parser import BookParser, BookValidator, process_all_books; print('✓ Imports work')"

# 4. Run a test validation
python gutenberg_cli.py validate --json-dir gutenberg_json --texts-dir gutenberg_texts
```