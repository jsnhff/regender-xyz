# /profile

Deep performance profiling and optimization recommendations.

## Usage

```bash
/profile [target] [options]
```

## Targets

- `book <path>` - Profile specific book processing
- `service <name>` - Profile service performance
- `providers` - Compare provider performance
- `memory` - Memory usage analysis
- `bottlenecks` - Find performance bottlenecks
- `all` - Comprehensive profiling

## Options

- `--iterations <n>` - Number of profiling runs
- `--size <small|medium|large>` - Test data size
- `--output <format>` - Output format (text|json|html)
- `--optimize` - Apply optimizations

## Workflow Pattern

### Phase 1: Profiling (Parallel)
```yaml
Agents:
  - backend-specialist: Profile code execution
  - qa-specialist: Measure quality metrics
  - ux-designer: Measure UX responsiveness

Output: Performance data and bottlenecks
```

### Phase 2: Analysis & Optimization (Sequential)
```yaml
Agents:
  - backend-specialist: Analyze results and suggest optimizations
  - senior-software-engineer: Implement optimizations
  - qa-specialist: Verify improvements

Output: Optimized code with metrics
```

## Profiling Examples

### Book Processing Performance
```bash
/profile book "pride_and_prejudice.txt" --iterations 5
```

Output:
```
=== Book Processing Profile ===

File: pride_and_prejudice.txt (758KB)

Processing Pipeline:
┌─────────────────┬──────────┬──────────┬────────┐
│ Stage           │ Time (s) │ Memory   │ Tokens │
├─────────────────┼──────────┼──────────┼────────┤
│ File Loading    │ 0.012    │ 2 MB     │ -      │
│ Text Parsing    │ 0.234    │ 18 MB    │ -      │
│ Character ID    │ 2.451    │ 45 MB    │ 18,234 │
│ Transformation  │ 4.892    │ 62 MB    │ 42,891 │
│ Quality Check   │ 1.234    │ 34 MB    │ 12,456 │
│ Output Format   │ 0.089    │ 8 MB     │ -      │
└─────────────────┴──────────┴──────────┴────────┘

Total Time: 8.912s
Peak Memory: 62 MB
Total Tokens: 73,581
Estimated Cost: $0.147

Bottlenecks Identified:
1. Transformation stage (55% of time)
   - Cause: Sequential paragraph processing
   - Fix: Batch paragraphs for LLM calls

2. Character identification (28% of time)
   - Cause: Redundant API calls
   - Fix: Cache character analysis

3. Memory spike during transformation
   - Cause: Loading entire book in memory
   - Fix: Stream processing for large files
```

### Provider Comparison
```bash
/profile providers --size medium
```

Results:
```
=== Provider Performance Comparison ===

Test: Transform 10 chapters (medium complexity)

OpenAI GPT-4:
├─ Average Response: 1.8s
├─ Token Throughput: 2,340 tokens/s
├─ Success Rate: 99.8%
├─ Cost per 1K tokens: $0.03
└─ Quality Score: 96%

Anthropic Claude:
├─ Average Response: 1.4s
├─ Token Throughput: 2,890 tokens/s
├─ Success Rate: 99.9%
├─ Cost per 1K tokens: $0.024
└─ Quality Score: 97%

Local MLX:
├─ Average Response: 3.2s
├─ Token Throughput: 890 tokens/s
├─ Success Rate: 98.5%
├─ Cost per 1K tokens: $0.00
└─ Quality Score: 89%

Recommendation: Use Claude for best balance
```

### Memory Profiling
```bash
/profile memory --size large
```

Analysis:
```
=== Memory Usage Profile ===

Memory Timeline:
     0s │  10MB │ ▁▁▁▁ Application start
   0.5s │  15MB │ ▂▂▂▂ Config loaded
   1.0s │  45MB │ ████ Book loaded
   2.0s │ 120MB │ ████████ Parsing complete
   3.0s │ 180MB │ ████████████ Characters analyzed
   4.0s │ 210MB │ ██████████████ Peak during transform
   5.0s │  90MB │ ██████ GC collected
   6.0s │  45MB │ ███ Output generated

Memory Allocations by Component:
├─ Book Model: 45 MB (21%)
├─ Character Cache: 68 MB (32%)
├─ LLM Responses: 82 MB (39%)
├─ Temporary Buffers: 15 MB (7%)
└─ Other: 2 MB (1%)

Optimization Opportunities:
1. Stream large books (save 40MB)
2. Clear character cache per chapter (save 50MB)
3. Process responses incrementally (save 60MB)

Potential Memory Savings: 150MB (71%)
```

### Bottleneck Analysis
```bash
/profile bottlenecks
```

Detailed bottleneck report:
```
=== Performance Bottleneck Analysis ===

Top 5 Bottlenecks:

1. CHARACTER EXTRACTION (38% of runtime)
   Location: character_service.py:45-89

   Current Implementation:
   for paragraph in chapter.paragraphs:
       characters = extract_characters(paragraph)

   Optimization:
   # Batch multiple paragraphs
   batch = []
   for paragraph in chapter.paragraphs:
       batch.append(paragraph)
       if len(batch) >= 10:
           characters = extract_characters_batch(batch)
           batch = []

   Expected Improvement: 65% faster

2. TOKEN COUNTING (12% of runtime)
   Location: providers/base.py:23

   Issue: Counting tokens for every call
   Solution: Cache token counts by content hash
   Expected Improvement: 90% faster for repeated content

3. JSON SERIALIZATION (8% of runtime)
   Location: Multiple locations

   Issue: Using standard json library
   Solution: Use orjson for faster serialization
   Expected Improvement: 4x faster

4. SYNCHRONOUS FILE I/O (6% of runtime)
   Location: parser_service.py:12

   Issue: Blocking I/O in async context
   Solution: Use aiofiles for async file operations
   Expected Improvement: Non-blocking I/O

5. REDUNDANT VALIDATION (5% of runtime)
   Location: transform_service.py:234

   Issue: Validating same data multiple times
   Solution: Validate once and cache results
   Expected Improvement: 80% reduction
```

### Optimization Mode
```bash
/profile all --optimize
```

Automatically applies optimizations:
```
=== Auto-Optimization Results ===

Optimizations Applied:
✓ Added caching to character extraction
✓ Implemented batch processing for LLM calls
✓ Switched to orjson for JSON operations
✓ Added async file operations
✓ Implemented connection pooling

Performance Improvements:
├─ Overall Speed: 3.2x faster
├─ Memory Usage: 45% reduction
├─ Token Efficiency: 23% fewer tokens
├─ Cost Reduction: 31% lower
└─ Quality Maintained: 97% score

Before: 8.9s / 210MB / $0.147
After:  2.8s / 115MB / $0.101

Code Changes:
- Modified 12 files
- Added 3 caching layers
- Introduced 2 new dependencies
- All tests passing
```

## Continuous Profiling

### Set Up Monitoring
```bash
/profile --monitor
```

Creates performance tracking:
```python
# Added to services/base.py
@performance_monitor
async def process(self, data):
    with timer("process_duration"):
        result = await self._process_internal(data)

    metrics.record("process_memory", get_memory_usage())
    metrics.record("process_tokens", count_tokens(result))

    return result
```

### Performance Regression Detection
```bash
/profile --baseline baseline.json
```

Compares against baseline:
```
=== Performance Regression Check ===

Comparing to baseline (v1.2.0):

Speed Metrics:
✓ Book parsing: 0.23s → 0.21s (+9% faster)
✗ Character ID: 2.1s → 2.5s (-19% slower) ⚠️
✓ Transformation: 4.8s → 4.2s (+13% faster)

Memory Metrics:
✓ Peak memory: 210MB → 180MB (+14% better)
✓ Average memory: 120MB → 105MB (+13% better)

REGRESSION DETECTED:
Character identification is 19% slower

Investigating cause...
Found: New validation added in commit abc123
Recommendation: Cache validation results
```

## Output Formats

### HTML Report
```bash
/profile all --output html > profile.html
```

Generates interactive report with:
- Flame graphs
- Memory timeline
- Cost analysis
- Optimization suggestions

### JSON Export
```bash
/profile all --output json
```

Machine-readable format for CI/CD:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "metrics": {
    "speed": {
      "total_seconds": 8.912,
      "stages": {...}
    },
    "memory": {
      "peak_mb": 210,
      "average_mb": 120
    },
    "cost": {
      "total_usd": 0.147,
      "per_1k_tokens": 0.02
    }
  },
  "bottlenecks": [...],
  "recommendations": [...]
}
```