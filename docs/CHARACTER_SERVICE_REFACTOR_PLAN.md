# Character Service Refactoring Plan

## Current State (September 21, 2025)

### Overview of Current Implementation

The character service (`src/services/character_service.py`) has evolved into a complex system that attempts to intelligently extract and deduplicate characters from literary texts. While functional, it has become over-engineered and has significant performance issues.

### How It Currently Works

#### Phase 1: Character Extraction
1. **Text Chunking** (Lines 543-565)
   - Splits book into ~2000 token chunks
   - Each chunk processed independently
   - Uses temperature=0.3 for consistency
   - Extracts raw character mentions with metadata

2. **Raw Character Collection**
   - Each character tagged with source chunk and context
   - No deduplication at this stage
   - Typically extracts 20-50 raw mentions for a short book

#### Phase 2: Global Deduplication
1. **Grouping Algorithm** (Lines 623-649)
   - Groups potentially similar characters
   - **PROBLEM**: O(n²) complexity with nested loops
   - Uses overly broad matching (any shared words = potential match)
   - Creates groups where characters might be the same person

2. **LLM Deduplication** (Lines 567-621)
   - Sends ALL character groups to LLM in single call
   - LLM decides which characters in each group are the same
   - Returns primary name and aliases for merged characters
   - **PROBLEM**: Single point of failure, no retry logic

3. **Result Application** (Lines 756-798)
   - Parses LLM response (fragile JSON parsing)
   - Creates final Character objects with aliases
   - Falls back to simple name-based dedup if LLM fails

### Current Problems

#### Critical Issues
1. **Performance**: O(n²) grouping algorithm becomes unusable with >100 characters
2. **Over-broad Matching**: "Tom" matches "Thomas Jefferson" causing incorrect groupings
3. **Fragile Parsing**: Single attempt at JSON parsing, often fails
4. **No Retry Logic**: One LLM failure breaks entire deduplication

#### Complexity Issues
1. **Method Too Long**: `_global_llm_deduplication` is 54 lines
2. **Mixed Responsibilities**: Methods do too many things
3. **Hard-coded Logic**: Temperature, prompts, thresholds all embedded
4. **Poor Testability**: Direct LLM calls, no abstraction

#### What's Overbuilt
1. **Smart Character Registry** (removed but remnants remain)
2. **Complex caching logic** (Lines 24-187) - rarely helps
3. **Token management integration** - adds complexity without clear benefit
4. **Progress logging** - too verbose for production

## Proposed Refactoring

### Simplification Goals
1. **Remove unnecessary complexity** - Strip out caching, token management
2. **Improve performance** - Replace O(n²) with O(n log n) algorithm
3. **Increase reliability** - Add retry logic, better error handling
4. **Enhance testability** - Extract LLM calls, use dependency injection

### New Architecture

```
CharacterService (Simplified Orchestrator)
├── CharacterExtractor (Phase 1)
│   ├── Extract characters from chunks
│   └── Return raw character list
├── CharacterGrouper (Phase 2a)
│   ├── Group similar characters efficiently
│   └── Use proper clustering algorithm
└── CharacterMerger (Phase 2b)
    ├── Send groups to LLM for verification
    ├── Parse responses robustly
    └── Apply merge decisions
```

### Implementation Plan

#### Step 1: Refactor Within Existing File
Instead of creating new files, we'll refactor the existing character_service.py to have cleaner internal organization. The methods will be reorganized but stay in the same file initially.

```python
class CharacterService:
    # Keep the same external interface
    # Reorganize internal methods into logical groups:

    # === EXTRACTION METHODS ===
    async def _extract_characters(self, text: str) -> List[Dict]:
        """Extract raw character mentions from text chunks."""
        pass

    # === GROUPING METHODS ===
    def _group_similar(self, characters: List[Dict]) -> List[List[Dict]]:
        """Group potentially similar characters efficiently."""
        pass

    # === MERGING METHODS ===
    async def _merge_groups(self, groups: List[List[Dict]]) -> List[Character]:
        """Use LLM to intelligently merge character groups."""
        pass
```

#### Step 2: Optimize Grouping Algorithm
```python
def group_similar_optimized(self, characters: List[RawCharacter]) -> List[CharacterGroup]:
    """O(n log n) grouping using efficient clustering."""
    # Option 1: Use sklearn's DBSCAN with string similarity
    # Option 2: Build similarity graph with Union-Find
    # Option 3: Use sorted lists with sliding window

    # Recommended: Union-Find with similarity threshold
    uf = UnionFind(len(characters))

    # Build similarity pairs (only check promising pairs)
    for i, char1 in enumerate(characters):
        # Only check characters with overlapping name tokens
        candidates = self._find_candidates(char1, characters[i+1:])
        for j, char2 in candidates:
            if self._similarity(char1, char2) > threshold:
                uf.union(i, j)

    return uf.get_groups()
```

#### Step 3: Robust JSON Parsing
```python
def parse_llm_response(self, response: str) -> Dict:
    """Parse LLM response with multiple strategies."""
    strategies = [
        lambda r: json.loads(r),                    # Direct parse
        lambda r: json.loads(self._clean_json(r)),  # Clean first
        lambda r: self._extract_json(r),            # Extract from markdown
        lambda r: self._regex_parse(r),             # Regex fallback
    ]

    for strategy in strategies:
        try:
            result = strategy(response)
            if self._validate_result(result):
                return result
        except Exception:
            continue

    raise ParseError("Could not parse LLM response")
```

#### Step 4: Configuration Externalization
```json
// src/config.json
{
  "services": {
    "character": {
      "extraction": {
        "chunk_size": 2000,
        "temperature": 0.3,
        "max_retries": 3
      },
      "grouping": {
        "algorithm": "union_find",
        "similarity_threshold": 0.7,
        "max_group_size": 20
      },
      "merging": {
        "temperature": 0.3,
        "timeout": 30,
        "batch_size": 50
      }
    }
  }
}
```

#### Step 5: Update Main Service In-Place
```python
class CharacterService:
    """Refactored character service with cleaner separation."""

    def __init__(self, provider, config=None):
        # Keep existing interface for compatibility
        self.provider = provider
        self.config = config or self._default_config()

        # Internal components (not separate files initially)
        self._init_components()

    def _init_components(self):
        """Initialize internal components."""
        # These can be extracted to separate files later if needed
        self.extractor = self._create_extractor()
        self.grouper = self._create_grouper()
        self.merger = self._create_merger()

    async def analyze_book(self, book: Book) -> CharacterAnalysis:
        """Direct replacement of existing method."""
        # Step 1: Extract
        raw_characters = await self._extract_characters(book.text)

        # Step 2: Group
        character_groups = self._group_similar(raw_characters)

        # Step 3: Merge
        final_characters = await self._merge_groups(character_groups)

        return CharacterAnalysis(
            book_id=book.id,
            characters=final_characters,
            metadata=self._calculate_stats(raw_characters, final_characters)
        )
```

## Implementation Strategy

### Phase 1: Direct Refactoring (Day 1-2)
1. **Morning**: Back up current character_service.py
2. **Afternoon**: Extract the three core components (Extractor, Grouper, Merger)
3. **Next Day**: Replace existing implementation entirely

### Phase 2: Core Improvements (Day 3)
1. **Replace grouping algorithm** with O(n log n) Union-Find
2. **Implement robust JSON parsing** with multiple strategies
3. **Add retry logic** with exponential backoff
4. **Externalize configuration** to config.json

### Phase 3: Testing & Validation (Day 4)
1. Test on standard corpus (5 books)
2. Verify performance improvements
3. Ensure consistent character counts

### Phase 4: Cleanup (Day 5)
1. Remove all dead code
2. Update documentation
3. Ensure all tests pass

## Success Metrics

### Performance
- **Current**: ~40s for "A Modest Proposal" (27 characters)
- **Target**: <10s for same book
- **Measure**: 75% reduction in processing time

### Reliability
- **Current**: ~20% failure rate on complex books
- **Target**: <5% failure rate
- **Measure**: Retry logic catches 90% of transient failures

### Accuracy
- **Current**: 27-33 characters (inconsistent)
- **Target**: Consistent count ±2 characters
- **Measure**: 5 runs produce same count

### Code Quality
- **Current**: 1000+ lines in single file
- **Target**: 3 files, <300 lines each
- **Measure**: Each method <20 lines

## Risk Mitigation

### Risk 1: Breaking Changes
- **Mitigation**: Create backup of current service before starting
- **Rollback**: Git revert if critical issues found

### Risk 2: Different Results
- **Mitigation**: Test thoroughly before committing
- **Acceptance**: Some differences OK if more accurate and consistent

### Risk 3: Performance Regression
- **Mitigation**: Benchmark before committing changes
- **Threshold**: Must be at least 2x faster

## Decision Points

### Before Starting
1. **Do we need character caching?** (Recommend: No, adds complexity)
2. **Should we keep token management?** (Recommend: No, not useful)
3. **How important is backward compatibility?** (Recommend: Low, focus on correctness)

### During Implementation
1. **Which grouping algorithm?** (Recommend: Union-Find)
2. **Retry strategy?** (Recommend: Exponential backoff, max 3)
3. **Batch processing?** (Recommend: Yes, groups of 50)

## Next Steps

1. **Back up current character_service.py**
2. **Start refactoring in place** - No new files, just reorganize existing code
3. **Test on small book first** - A Modest Proposal
4. **Implement improvements incrementally** - Grouping algorithm, then parsing, then retry logic
5. **Commit once working** - Single commit with all improvements

## Notes for Future Developer

The current implementation grew organically and accumulated complexity. The main insight is that we don't need perfect deduplication - we need consistent, fast, and good-enough deduplication.

Key learnings:
- LLMs are good at verification, not discovery
- Simple algorithms with LLM verification beats complex algorithms
- Configuration should be external, not embedded
- Testability requires abstraction of external calls

The refactored version should be dramatically simpler while being more reliable and faster.