# Code Improvement Plan for Regender-XYZ
## Generated from Deep Code Analysis - September 21, 2025

## Executive Summary
The codebase has 282 linting issues, critical async/sync mixing problems, missing error handling, and performance bottlenecks. This plan addresses these issues in priority order.

## Priority Classification
- 🔴 **CRITICAL**: System crashes or data loss possible
- 🟡 **HIGH**: Performance or reliability issues
- 🟢 **MEDIUM**: Code quality and maintainability
- 🔵 **LOW**: Nice-to-have improvements

---

## Phase 1: Critical Fixes (Day 1-2)
*These issues can cause system crashes and must be fixed immediately*

### 1.1 Fix Async/Sync Mixing 🔴
**Files**: `src/services/character_service.py`
**Issue**: Heavy sync operations in async methods block the event loop
**Fix**:
```python
# Add async wrapper for CPU-bound operations
async def _create_chunks_async(self, text: str) -> list[str]:
    return await asyncio.to_thread(self._create_chunks, text)
```
**Tasks**:
- [ ] Make `_create_chunks` async or use `asyncio.to_thread()`
- [ ] Make `_group_characters` async or use thread wrapper
- [ ] Fix `_merge_character_group` to be async-safe
- [ ] Test with large books to ensure no blocking

### 1.2 Add Error Handling to Provider Calls 🔴
**Files**: `src/providers/openai.py`, `src/providers/anthropic.py`
**Issue**: No error handling for rate limits, network errors, or API failures
**Fix**:
```python
async def complete(self, messages, **kwargs):
    try:
        response = await self._complete_with_retry(messages, **kwargs)
        return response
    except RateLimitError as e:
        await asyncio.sleep(60)  # Back off on rate limit
        return await self.complete(messages, **kwargs)
    except TimeoutError:
        raise ProviderTimeoutError(f"Provider {self.name} timed out")
    except Exception as e:
        logger.error(f"Provider error: {e}")
        raise ProviderError(f"Provider {self.name} failed: {e}")
```
**Tasks**:
- [ ] Add try/catch to all provider `complete()` methods
- [ ] Implement exponential backoff for rate limits
- [ ] Add timeout handling with clear error messages
- [ ] Create custom exception classes for provider errors
- [ ] Add circuit breaker pattern for repeated failures

### 1.3 Fix CLI Async Integration 🔴
**File**: `regender_cli.py`
**Issue**: CLI doesn't properly handle async services
**Fix**:
```python
def main():
    """Main entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
```
**Tasks**:
- [ ] Wrap main CLI logic in `asyncio.run()`
- [ ] Add proper async context managers
- [ ] Handle KeyboardInterrupt gracefully
- [ ] Ensure all async resources are cleaned up

### 1.4 Fix Import and Syntax Issues 🔴
**All files**
**Issue**: 282 linting errors including import issues
**Tasks**:
- [ ] Run `ruff check --fix src/` to auto-fix 10 issues
- [ ] Fix remaining import order issues manually
- [ ] Update type hints from `Dict` to `dict`, `List` to `list`
- [ ] Remove unused imports
- [ ] Add missing newlines at end of files

---

## Phase 2: High Priority Performance (Day 3-4)
*These issues cause significant performance degradation*

### 2.1 Implement Parallel Chunk Processing 🟡
**File**: `src/services/character_service.py`
**Issue**: Sequential processing of chunks (takes 14 minutes for Pride & Prejudice)
**Fix**:
```python
async def _extract_all_characters(self, text: str) -> list[dict]:
    chunks = self._create_chunks(text)

    # Process chunks in parallel (max 5 concurrent)
    semaphore = asyncio.Semaphore(5)

    async def process_with_limit(chunk, idx):
        async with semaphore:
            return await self._extract_from_chunk(chunk, idx)

    tasks = [process_with_limit(chunk, i) for i, chunk in enumerate(chunks)]
    results = await asyncio.gather(*tasks)

    # Flatten results
    all_characters = []
    for chars in results:
        all_characters.extend(chars)

    return all_characters
```
**Tasks**:
- [ ] Add `asyncio.gather()` for parallel chunk processing
- [ ] Implement semaphore to limit concurrent API calls
- [ ] Add progress reporting for long operations
- [ ] Test with rate limiting to ensure stability

### 2.2 Add Caching Layer 🟡
**Files**: `src/services/character_service.py`
**Issue**: Same characters analyzed multiple times
**Fix**:
```python
from functools import lru_cache
import hashlib

class CharacterService:
    def __init__(self):
        self._cache = {}

    async def analyze(self, book: Book) -> CharacterAnalysis:
        # Create cache key from book content
        book_hash = hashlib.md5(book.to_json().encode()).hexdigest()

        if book_hash in self._cache:
            logger.info("Using cached character analysis")
            return self._cache[book_hash]

        # Perform analysis
        result = await self._analyze_impl(book)
        self._cache[book_hash] = result
        return result
```
**Tasks**:
- [ ] Add in-memory cache for character analysis
- [ ] Implement cache key generation from book content
- [ ] Add cache expiration (1 hour TTL)
- [ ] Add cache statistics logging
- [ ] Consider persistent cache with Redis/SQLite

### 2.3 Optimize Batch Sizes 🟡
**File**: `src/config.json`
**Issue**: Inefficient batch sizes not using full context window
**Current**: 100 paragraphs per batch
**Target**: Dynamic based on token count
**Tasks**:
- [ ] Implement dynamic batching based on token count
- [ ] Use TokenManager to estimate batch sizes
- [ ] Aim for 80% of context window utilization
- [ ] Add configuration for max tokens per request

---

## Phase 3: Code Quality Improvements (Day 5-6)
*These issues affect maintainability and reliability*

### 3.1 Simplify Configuration System 🟢
**Files**: `src/container.py`, `src/config.json`, `src/simple_config.py`
**Issue**: Overly complex DI container for simple needs
**Tasks**:
- [ ] Complete migration to `simple_config.py`
- [ ] Remove complex container.py (75 lines of unnecessary complexity)
- [ ] Update all services to use simple_config
- [ ] Remove ServiceConfig dataclass complexity
- [ ] Add environment variable overrides

### 3.2 Extract Common Transform Logic 🟢
**File**: `src/services/transform_service.py`
**Issue**: 30% code duplication across transform methods
**Fix**:
```python
async def _apply_transformation(
    self,
    book: Book,
    transform_type: TransformType,
    characters: CharacterAnalysis
) -> Transformation:
    """Common transformation logic for all types."""
    # Single implementation for all transform types
    prompt = self._build_transform_prompt(transform_type, characters)

    # Process all chapters with same logic
    for chapter in book.chapters:
        transformed = await self._transform_chapter(chapter, prompt)
        # ... common processing
```
**Tasks**:
- [ ] Create base `_apply_transformation` method
- [ ] Remove duplicate code from each transform method
- [ ] Consolidate prompt building logic
- [ ] Add transform type registry pattern

### 3.3 Improve Error Messages 🟢
**All service files**
**Issue**: Generic error messages without context
**Fix**:
```python
except Exception as e:
    logger.error(
        f"Character extraction failed for chunk {chunk_idx} "
        f"({len(chunk)} chars): {e}",
        extra={"chunk_preview": chunk[:100], "error_type": type(e).__name__}
    )
    raise CharacterExtractionError(
        f"Failed to extract characters from chunk {chunk_idx}"
    ) from e
```
**Tasks**:
- [ ] Add context to all error messages
- [ ] Include relevant data in log extras
- [ ] Create custom exception hierarchy
- [ ] Add error recovery suggestions

### 3.4 Add Input Validation 🟢
**All service methods**
**Issue**: No validation of inputs
**Fix**:
```python
def validate_book(book: Book) -> None:
    """Validate book before processing."""
    if not book.chapters:
        raise ValueError("Book has no chapters")
    if not book.title:
        raise ValueError("Book has no title")
    total_text = sum(len(c.get_text()) for c in book.chapters)
    if total_text < 100:
        raise ValueError(f"Book too short: {total_text} chars")
```
**Tasks**:
- [ ] Add validation to all public methods
- [ ] Check for empty/null inputs
- [ ] Validate configuration values
- [ ] Add size limits for safety

---

## Phase 4: Architecture Refactoring (Day 7-8)
*Long-term improvements for maintainability*

### 4.1 Create Provider Interface 🔵
**File**: `src/providers/base_provider.py`
**Issue**: Inconsistent provider implementations
**Fix**:
```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict], **kwargs) -> str:
        """Complete a chat conversation."""
        pass

    @abstractmethod
    async def get_rate_limits(self) -> dict:
        """Get current rate limit status."""
        pass
```
**Tasks**:
- [ ] Define clear provider interface
- [ ] Ensure all providers implement it
- [ ] Add provider capability detection
- [ ] Standardize error handling

### 4.2 Implement Circuit Breaker 🔵
**New file**: `src/utils/circuit_breaker.py`
**Issue**: No protection against cascading failures
**Tasks**:
- [ ] Implement circuit breaker pattern
- [ ] Add failure threshold configuration
- [ ] Implement half-open state testing
- [ ] Add metrics and alerting

### 4.3 Add Progress Reporting 🔵
**All long-running operations**
**Issue**: No feedback during long operations
**Fix**:
```python
from tqdm import tqdm

async def process_chunks(chunks):
    with tqdm(total=len(chunks), desc="Extracting characters") as pbar:
        for chunk in chunks:
            result = await process_chunk(chunk)
            pbar.update(1)
            pbar.set_postfix({"chars_found": len(result)})
```
**Tasks**:
- [ ] Add tqdm progress bars
- [ ] Implement progress callbacks
- [ ] Add ETA calculations
- [ ] Support quiet mode for CI/CD

---

## Testing Plan

### Unit Tests Needed
- [ ] Test async/sync wrappers
- [ ] Test error handling in providers
- [ ] Test caching logic
- [ ] Test parallel processing
- [ ] Test input validation

### Integration Tests Needed
- [ ] Test full pipeline with small book
- [ ] Test error recovery
- [ ] Test rate limit handling
- [ ] Test cache effectiveness

### Performance Tests Needed
- [ ] Measure improvement from parallel processing
- [ ] Benchmark cache hit rates
- [ ] Test memory usage with large books
- [ ] Measure API call reduction

---

## Success Metrics

### Performance Targets
- Character extraction: < 5 minutes for full novels (currently 14 minutes)
- API calls: 75% reduction through better batching
- Memory usage: < 500MB for largest books
- Cache hit rate: > 80% for repeated operations

### Quality Targets
- Linting errors: 0 (currently 282)
- Test coverage: > 80%
- Error handling: 100% of API calls wrapped
- Documentation: All public methods documented

---

## Implementation Schedule

| Day | Phase | Tasks | Priority |
|-----|-------|-------|----------|
| 1-2 | Critical Fixes | Async/sync, error handling, CLI | 🔴 |
| 3-4 | Performance | Parallel processing, caching | 🟡 |
| 5-6 | Code Quality | Config, duplication, validation | 🟢 |
| 7-8 | Architecture | Interfaces, circuit breaker | 🔵 |
| 9 | Testing | Unit and integration tests | 🟢 |
| 10 | Documentation | Update docs, add examples | 🔵 |

---

## Commands for Validation

```bash
# Fix linting issues
ruff check --fix src/
ruff format src/

# Test changes
python -m pytest tests/

# Performance test
time python regender_cli.py books/json/pg1342-Pride_and_Prejudice.json character_analysis --no-qc

# Memory profiling
mprof run python regender_cli.py books/json/pg43.json gender_swap
mprof plot

# Check for async issues
python -m pytest tests/ -W error::RuntimeWarning
```

---

## Risk Mitigation

### Potential Risks
1. **Breaking changes during refactoring**
   - Mitigation: Comprehensive test suite before changes
   - Rollback plan: Git tags for each phase

2. **Performance regression**
   - Mitigation: Benchmark before/after each change
   - Monitoring: Add performance logging

3. **API rate limits during testing**
   - Mitigation: Use mock providers for testing
   - Backup: Implement exponential backoff

---

## Notes

- Keep backward compatibility during migration
- Document all breaking changes
- Update README with new configuration
- Consider feature flags for gradual rollout
- Monitor error rates in production

---

*Last Updated: September 21, 2025*
*Generated from deep code analysis using Claude Code*