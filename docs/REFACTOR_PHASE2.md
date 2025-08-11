# Phase 2: Core Consolidation (1 Week)

## Overview
Eliminate redundancy and establish clear module boundaries. This phase involves significant code restructuring.

## Goals
- Eliminate all duplicate implementations
- Establish single source of truth for each function
- Implement parallel processing
- 5x performance improvement

## Prerequisites
- Phase 1 completed and stable
- Full test suite passing
- Performance baseline established

## Major Tasks

### Day 1-2: Unify Character Analysis

#### Task 2.1: Create Unified Character Analyzer
**New File**: `book_characters/unified_analyzer.py`
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from enum import Enum

class ChunkingStrategy(Enum):
    SEQUENTIAL = "sequential"
    SMART = "smart"
    RATE_LIMITED = "rate_limited"

class ChunkingStrategyBase(ABC):
    @abstractmethod
    def chunk_text(self, text: str, max_tokens: int) -> List[str]:
        pass

class SequentialChunking(ChunkingStrategyBase):
    def chunk_text(self, text: str, max_tokens: int) -> List[str]:
        # Implementation from analyzer.py
        pass

class SmartChunking(ChunkingStrategyBase):
    def chunk_text(self, text: str, max_tokens: int) -> List[str]:
        # Implementation from smart_chunked_analyzer.py
        pass

class RateLimitedChunking(ChunkingStrategyBase):
    def chunk_text(self, text: str, max_tokens: int) -> List[str]:
        # Implementation from rate_limited_analyzer.py
        pass

class UnifiedCharacterAnalyzer:
    """Single character analyzer with pluggable strategies."""
    
    def __init__(self, strategy: ChunkingStrategy = ChunkingStrategy.SMART):
        self.strategy = self._get_strategy(strategy)
        self.client = UnifiedLLMClient()
    
    def _get_strategy(self, strategy: ChunkingStrategy) -> ChunkingStrategyBase:
        strategies = {
            ChunkingStrategy.SEQUENTIAL: SequentialChunking(),
            ChunkingStrategy.SMART: SmartChunking(),
            ChunkingStrategy.RATE_LIMITED: RateLimitedChunking()
        }
        return strategies[strategy]
    
    def analyze(self, book_data: Dict, use_cache: bool = True) -> Dict:
        # Check cache first
        if use_cache:
            cached = load_cached_analysis(book_data)
            if cached:
                return cached
        
        # Extract text
        text = self._extract_text(book_data)
        
        # Chunk using strategy
        chunks = self.strategy.chunk_text(text, self._get_max_tokens())
        
        # Analyze chunks
        characters = {}
        for chunk in chunks:
            chunk_characters = self._analyze_chunk(chunk)
            characters = self._merge_characters(characters, chunk_characters)
        
        # Cache results
        if use_cache:
            cache_character_analysis(book_data, characters)
        
        return characters
```

#### Task 2.2: Update All Imports
```python
# Update book_transform/unified_transform.py
from book_characters import UnifiedCharacterAnalyzer

# Replace old imports
analyzer = UnifiedCharacterAnalyzer(strategy=ChunkingStrategy.SMART)
characters = analyzer.analyze(book_data)
```

#### Task 2.3: Remove Old Analyzers
```bash
# After testing, remove old files
git rm book_characters/analyzer.py
git rm book_characters/api_chunked_analyzer.py
git rm book_characters/rate_limited_analyzer.py
git rm book_characters/smart_chunked_analyzer.py
```

### Day 3-4: Consolidate Transformation Pipeline

#### Task 2.4: Refactor Transform Module
**Update**: `book_transform/transform.py`
```python
class BookTransformer:
    """Core transformation logic."""
    
    def __init__(self, client: UnifiedLLMClient = None):
        self.client = client or UnifiedLLMClient()
        self.chunker = SmartChunker()
    
    def transform_book(self, book_data: Dict, 
                       characters: Dict,
                       transform_type: str) -> Dict:
        """Single entry point for transformation."""
        # This becomes the ONLY transformation function
        transformed_chapters = []
        
        for chapter in book_data['chapters']:
            transformed = self.transform_chapter(
                chapter, characters, transform_type
            )
            transformed_chapters.append(transformed)
        
        return {
            'chapters': transformed_chapters,
            'metadata': self._create_metadata(transform_type)
        }
    
    def transform_chapter(self, chapter: Dict, 
                         characters: Dict,
                         transform_type: str) -> Dict:
        """Transform a single chapter."""
        # Consolidated logic from all transform files
        pass
```

#### Task 2.5: Update Unified Transform
**File**: `book_transform/unified_transform.py`
```python
from book_transform.transform import BookTransformer

class UnifiedBookTransformer:
    def __init__(self):
        self.transformer = BookTransformer()
        self.qc = QualityController()
    
    def transform_book_unified(self, ...):
        # Now uses single BookTransformer
        transformed = self.transformer.transform_book(...)
        
        # Add QC on top
        if quality_level > 0:
            transformed = self.qc.improve_quality(transformed)
        
        return transformed
```

#### Task 2.6: Remove Duplicate Transform Code
```bash
# Remove after consolidation
git rm book_transform/llm_transform.py

# Update __init__.py to export only unified interface
```

### Day 5: Implement Parallel Processing

#### Task 2.7: Add Async Support to API Client
**File**: `api_client.py`
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncLLMClient:
    """Async wrapper for LLM clients."""
    
    def __init__(self, client: UnifiedLLMClient):
        self.client = client
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def complete_async(self, messages, **kwargs):
        """Async completion."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.client.complete,
            messages,
            **kwargs
        )
```

#### Task 2.8: Parallel Chapter Processing
**File**: `book_transform/parallel_transform.py`
```python
import asyncio
from typing import List, Dict

class ParallelTransformer:
    """Process multiple chapters in parallel."""
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def transform_chapters_parallel(self, 
                                         chapters: List[Dict],
                                         characters: Dict,
                                         transform_type: str) -> List[Dict]:
        """Transform chapters in parallel."""
        tasks = []
        for chapter in chapters:
            task = self._transform_with_limit(
                chapter, characters, transform_type
            )
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    async def _transform_with_limit(self, chapter, characters, transform_type):
        """Transform with concurrency limit."""
        async with self.semaphore:
            return await self._transform_chapter_async(
                chapter, characters, transform_type
            )
```

#### Task 2.9: Integration with Main Pipeline
**Update**: `book_transform/unified_transform.py`
```python
def transform_book_unified(self, book_data, ...):
    # Detect if we should use parallel processing
    if len(book_data['chapters']) > 5:
        # Use parallel for books with many chapters
        transformed = asyncio.run(
            self.parallel_transformer.transform_chapters_parallel(
                book_data['chapters'],
                characters,
                transform_type
            )
        )
    else:
        # Sequential for small books
        transformed = self.transformer.transform_book(...)
```

## Module Structure After Phase 2

```
book_characters/
├── __init__.py
├── unified_analyzer.py      # Single analyzer with strategies
├── strategies/
│   ├── __init__.py
│   ├── sequential.py
│   ├── smart.py
│   └── rate_limited.py
├── cache.py                # Caching utilities
└── prompts.py              # Character analysis prompts

book_transform/
├── __init__.py
├── transform.py            # Core transformation logic
├── unified_transform.py    # Pipeline orchestration
├── parallel_transform.py   # Parallel processing
├── quality_control.py      # QC module
└── chunking/
    └── token_utils.py      # Single chunking implementation
```

## Testing Strategy

### Unit Tests
```python
# tests/test_unified_character_analyzer.py
def test_analyzer_strategies():
    """Test all chunking strategies produce valid results."""
    for strategy in ChunkingStrategy:
        analyzer = UnifiedCharacterAnalyzer(strategy=strategy)
        result = analyzer.analyze(sample_book)
        assert 'characters' in result

def test_parallel_transformation():
    """Test parallel processing produces same results."""
    sequential_result = transform_sequential(book)
    parallel_result = asyncio.run(transform_parallel(book))
    assert sequential_result == parallel_result
```

### Integration Tests
```python
# tests/test_end_to_end_phase2.py
def test_complete_pipeline():
    """Test entire pipeline with new unified modules."""
    # Download → Parse → Analyze → Transform → QC
    pass
```

### Performance Tests
```python
# tests/benchmark_phase2.py
def benchmark_parallel_vs_sequential():
    """Compare parallel vs sequential performance."""
    # Should show 3-5x improvement for multi-chapter books
    pass
```

## Migration Guide

### For Existing Code
```python
# Old way (multiple options):
from book_characters import analyze_book_characters
from book_characters.smart_chunked_analyzer import SmartChunkedAnalyzer
from book_transform import transform_book

# New way (single clear path):
from book_characters import UnifiedCharacterAnalyzer
from book_transform import UnifiedBookTransformer

analyzer = UnifiedCharacterAnalyzer()
transformer = UnifiedBookTransformer()
```

### For CLI Users
No changes - all commands work the same:
```bash
python regender_book_cli.py regender book.txt
```

## Risk Management

### Potential Issues
1. **Parallel processing rate limits**: Implement backoff
2. **Memory usage with async**: Monitor and limit concurrent tasks
3. **Character merging conflicts**: Extensive testing of merge logic

### Rollback Points
- Before removing old analyzers (Day 2)
- Before implementing parallel processing (Day 5)
- Keep feature flag for parallel vs sequential

## Performance Targets

### Expected Improvements
- **Sequential books**: 2x faster (from consolidation)
- **Multi-chapter books**: 5x faster (from parallelization)
- **Memory usage**: Stable (async overhead minimal)
- **Code maintainability**: 10x better (single path)

### Benchmarks to Run
```bash
# Before refactoring
time python regender_book_cli.py regender books/texts/pg1342.txt

# After refactoring
time python regender_book_cli.py regender books/texts/pg1342.txt

# Should show 5x improvement
```

## Next Steps

1. Complete Phase 2 implementation
2. Run full regression suite
3. Performance validation
4. Update documentation
5. Proceed to Phase 3 (Architecture)

## Notes

- Keep backward compatibility during transition
- Extensive testing at each step
- Document all API changes
- Consider feature flags for gradual rollout