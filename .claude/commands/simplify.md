# /simplify

Reduce complexity and improve code clarity across the codebase.

## Usage

```bash
/simplify [target] [options]
```

## Targets

- `all` - Entire codebase
- `complex` - Focus on complex functions
- `duplicates` - Remove duplication
- `imports` - Clean up imports
- `types` - Simplify type hints
- `tests` - Simplify test structure

## Options

- `--threshold <n>` - Complexity threshold (default: 10)
- `--aggressive` - More aggressive simplification
- `--preserve-performance` - Don't sacrifice speed
- `--explain` - Explain each simplification

## Workflow Pattern

### Phase 1: Complexity Analysis (Parallel)
```yaml
Agents:
  - backend-specialist: Identify complex patterns
  - code-reviewer: Find code smells
  - qa-specialist: Identify test complexity

Output: Complexity heat map and targets
```

### Phase 2: Simplification (Sequential)
```yaml
Agents:
  - senior-software-engineer: Apply simplifications
  - code-reviewer: Verify improvements
  - qa-specialist: Ensure tests still pass

Output: Simplified code with metrics
```

## Simplification Patterns

### Complex Function Breakdown
```bash
/simplify complex --threshold 15
```

Before:
```python
def process_book(self, book_path, options):
    # 50+ lines of nested logic
    if os.path.exists(book_path):
        with open(book_path) as f:
            content = f.read()
            if options.get('parse'):
                parsed = self.parser.parse(content)
                if parsed:
                    if options.get('analyze'):
                        characters = []
                        for chapter in parsed.chapters:
                            for paragraph in chapter.paragraphs:
                                # More nested logic...
```

After:
```python
def process_book(self, book_path: str, options: Dict) -> Result:
    """Process a book with given options."""
    content = self._load_book(book_path)
    parsed = self._parse_if_needed(content, options)
    analyzed = self._analyze_if_needed(parsed, options)
    return self._transform(analyzed, options)

def _load_book(self, path: str) -> str:
    """Load book content from file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Book not found: {path}")
    return Path(path).read_text()

def _parse_if_needed(self, content: str, options: Dict) -> Optional[Book]:
    """Parse content if requested."""
    if not options.get('parse'):
        return None
    return self.parser.parse(content)
```

### Duplicate Code Elimination
```bash
/simplify duplicates
```

Identifies and refactors:
```python
# Before: Same pattern in 3 places
# In service_a.py
result = await provider.complete(prompt)
if not result:
    logger.error("Provider failed")
    raise ProviderError("No response")
parsed = json.loads(result)

# In service_b.py
result = await provider.complete(prompt)
if not result:
    logger.error("Provider failed")
    raise ProviderError("No response")
parsed = json.loads(result)

# After: Extracted to base class
class BaseService:
    async def _call_provider(self, prompt: str) -> Dict:
        """Call provider with standard error handling."""
        result = await self.provider.complete(prompt)
        if not result:
            logger.error("Provider failed")
            raise ProviderError("No response")
        return json.loads(result)
```

### Import Simplification
```bash
/simplify imports
```

Cleans up:
```python
# Before
from typing import Dict, List, Optional, Union, Any, Tuple, Set
from src.services.base import BaseService
from src.services.parser_service import ParserService
from src.models.book import Book
from src.models.character import Character
import os
import sys
import json
from pathlib import Path
import asyncio

# After
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models import Book, Character
from src.services import BaseService, ParserService
```

### Type Hint Simplification
```bash
/simplify types
```

Improves readability:
```python
# Before
def process(
    self,
    data: Union[Dict[str, Union[str, List[Dict[str, Any]]]], None],
    options: Optional[Dict[str, Union[bool, str, int]]] = None
) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:

# After
from typing import TypeAlias

BookData: TypeAlias = Dict[str, Any]
Options: TypeAlias = Dict[str, Any]

def process(
    self,
    data: Optional[BookData],
    options: Optional[Options] = None
) -> Optional[BookData]:
```

### Test Simplification
```bash
/simplify tests
```

Refactors test structure:
```python
# Before: Repetitive test setup
class TestCharacterService:
    def test_analyze_simple(self):
        service = CharacterService()
        service.provider = Mock()
        service.provider.complete.return_value = "response"
        book = Book(title="Test")
        result = service.analyze(book)
        assert result

    def test_analyze_complex(self):
        service = CharacterService()
        service.provider = Mock()
        service.provider.complete.return_value = "response"
        book = Book(title="Test", chapters=[...])
        result = service.analyze(book)
        assert result

# After: Clean fixtures
class TestCharacterService:
    @pytest.fixture
    def service(self):
        """Create service with mocked provider."""
        service = CharacterService()
        service.provider = Mock()
        service.provider.complete.return_value = "response"
        return service

    @pytest.fixture
    def simple_book(self):
        return Book(title="Test")

    def test_analyze_simple(self, service, simple_book):
        result = service.analyze(simple_book)
        assert result
```

## Complexity Metrics

Shows before/after metrics:
```
=== Simplification Report ===

Cyclomatic Complexity:
  Average: 8.3 → 4.2
  Maximum: 24 → 9
  Files > 10: 12 → 2

Code Duplication:
  Duplicate blocks: 18 → 3
  Lines saved: 284

Readability:
  Average line length: 92 → 78
  Nesting depth: 4.2 → 2.8
  Functions > 50 lines: 8 → 0

Type Coverage:
  Before: 67%
  After: 89%
  Simplified unions: 14

Test Clarity:
  Setup lines: 450 → 120
  Fixtures created: 12
  Test speed: 15% faster
```

## Aggressive Mode

```bash
/simplify all --aggressive
```

More dramatic changes:
- Extract all functions > 20 lines
- Remove all code duplication
- Enforce single responsibility
- Maximum nesting depth of 2
- No complex conditionals

## Performance Preservation

```bash
/simplify --preserve-performance
```

Ensures:
- No additional function calls in hot paths
- Maintains algorithmic complexity
- Preserves caching strategies
- Keeps optimized loops

## Explanation Mode

```bash
/simplify complex --explain
```

Provides reasoning:
```
Simplifying: transform_service.py::apply_transformation

Reason: Cyclomatic complexity of 18 (threshold: 10)

Changes:
1. Extract nested loop into _process_chapters()
   - Reduces nesting from 5 to 2
   - Improves testability

2. Replace if-elif chain with strategy pattern
   - Cleaner extension point
   - Reduces complexity by 6

3. Extract validation into _validate_input()
   - Single responsibility
   - Reusable validation

Result: Complexity reduced to 7
```

## Integration Benefits

Works with other commands:
- `/review` - Verify simplifications are correct
- `/test-deep` - Ensure no regressions
- `/profile` - Confirm performance maintained
- `/document` - Update docs for new structure