# /test-deep

Comprehensive testing with deep analysis of results, edge cases, and quality metrics.

## Usage

```bash
/test-deep <scope> [options]
```

## Scopes

- `transformation` - Test transformation accuracy and consistency
- `providers` - Test all LLM providers for consistency
- `edge-cases` - Test unusual inputs and edge conditions
- `performance` - Load testing and benchmarks
- `quality` - Transformation quality metrics
- `regression` - Compare against baseline results
- `all` - Complete test suite

## Options

- `--verbose` - Detailed output with examples
- `--compare` - Compare providers/versions
- `--fix` - Attempt to fix failing tests
- `--report` - Generate detailed HTML report
- `--threshold <n>` - Quality threshold (default: 0.85)

## Workflow Pattern

### Phase 1: Test Design (Parallel)
```yaml
Agents:
  - qa-specialist: Design comprehensive test scenarios
  - backend-specialist: Identify performance test points
  - ux-designer: Define CLI behavior tests

Output: Complete test plan with edge cases
```

### Phase 2: Execution & Analysis (Sequential)
```yaml
Agents:
  - qa-specialist: Run tests and collect results
  - backend-specialist: Analyze performance metrics
  - code-reviewer: Review test coverage and quality

Output: Detailed test results with analysis
```

### Phase 3: Remediation (Conditional)
```yaml
If failures detected:
  - senior-software-engineer: Fix identified issues
  - qa-specialist: Re-test affected areas
  - docs-specialist: Update documentation

Output: Fixed code with passing tests
```

## Test Categories

### Transformation Accuracy Testing
```bash
/test-deep transformation --verbose
```

Tests:
- Pronoun consistency across chapters
- Character gender persistence
- Narrative coherence
- Grammar preservation
- Context-dependent transformations

Example output:
```
=== Transformation Accuracy Report ===

✓ Pronoun Consistency: 98.5%
  - 2 inconsistencies found in chapter transitions

✓ Character Persistence: 100%
  - All characters maintain gender throughout

⚠ Context Handling: 87%
  - Ambiguous pronouns: 13 cases needed context
  - Successfully resolved: 11/13

✓ Grammar Integrity: 99.2%
  - Subject-verb agreement maintained
  - Possessive forms correct

Edge Cases:
  ✗ "They" as singular: Incorrectly pluralized verbs
  ✓ Nested quotes: Handled correctly
  ✓ Historical titles: Appropriately transformed
```

### Provider Consistency Testing
```bash
/test-deep providers --compare
```

Compares outputs across providers:
```
=== Provider Comparison ===

Test: "Gender swap on Pride and Prejudice excerpt"

OpenAI GPT-4:
  - Accuracy: 96%
  - Speed: 2.3s
  - Cost: $0.024

Anthropic Claude:
  - Accuracy: 97%
  - Speed: 1.9s
  - Cost: $0.018

Consistency Score: 94%
Differences:
  - Handling of "Mrs/Miss": OpenAI more conservative
  - Pronoun ambiguity: Claude better at context
```

### Edge Case Testing
```bash
/test-deep edge-cases
```

Tests unusual inputs:
```python
EDGE_CASES = [
    # Ambiguous names
    "Alex told Jordan they were ready",

    # Nested possession
    "She took her mother's friend's daughter's book",

    # Mixed pronouns in one sentence
    "He told her that they should meet their friends",

    # Historical/cultural specific
    "The duchess and the earl met at the viscount's estate",

    # Technical writing
    "The user must update their password when they login",

    # Poetry with complex structure
    """She walks in beauty, like the night
       Of cloudless climes and starry skies""",
]
```

### Performance Testing
```bash
/test-deep performance --report
```

Generates performance report:
```
=== Performance Metrics ===

Book Processing Speed:
  Small (<100KB): 0.8s average
  Medium (100KB-1MB): 4.2s average
  Large (>1MB): 18.5s average

Token Efficiency:
  Average tokens/paragraph: 127
  Wasted tokens (overlap): 8%
  Optimal chunk size: 2800 tokens

Memory Usage:
  Peak memory: 248MB
  Average memory: 156MB
  Memory per book MB: 12MB

Bottlenecks Identified:
  1. Character extraction: 38% of time
  2. LLM calls: 45% of time
  3. JSON parsing: 7% of time

Recommendations:
  - Cache character analysis
  - Batch LLM calls
  - Stream large files
```

### Quality Regression Testing
```bash
/test-deep regression --threshold 0.95
```

Compares against baseline:
```
=== Regression Test Results ===

Baseline: v1.2.0
Current: v1.3.0-dev

Quality Metrics:
  Pronoun Accuracy: 96% → 97% [+1%] ✓
  Grammar Score: 94% → 93% [-1%] ⚠
  Readability: 88% → 91% [+3%] ✓
  Consistency: 95% → 95% [0%] ✓

Regression Detected:
  - Grammar score decreased in poetry
  - Investigating root cause...

Recommendation: Fix before merge
```

## Advanced Testing Features

### Interactive Failure Analysis
```bash
/test-deep transformation --fix
```

When tests fail:
```
Test Failed: Inconsistent pronoun in chapter 3

Original: "She saw herself in the mirror"
Expected: "He saw himself in the mirror"
Actual: "He saw herself in the mirror"

Analyzing failure...
Root cause: Reflexive pronoun not updated

Would you like to:
1. View surrounding context
2. Test alternative approaches
3. Apply automatic fix
4. Skip and continue

Choice [1-4]: 3

Applying fix...
✓ Fixed and re-tested successfully
```

### Comparative Quality Analysis
```bash
/test-deep quality --compare baseline.json
```

Detailed quality comparison:
```
=== Quality Analysis ===

Readability Scores:
  Flesch Reading Ease: 72.3 → 71.8 (minimal change)
  Flesch-Kincaid Grade: 6.2 → 6.3 (maintained)

Sentiment Preservation:
  Positive passages: 98% preserved
  Negative passages: 96% preserved
  Neutral passages: 99% preserved

Character Voice Consistency:
  Elizabeth Bennet: 94% consistent
  Mr. Darcy: 97% consistent
  Minor characters: 89% consistent

Narrative Flow:
  Sentence transitions: Smooth (92%)
  Paragraph coherence: High (95%)
  Chapter continuity: Excellent (98%)
```

### Test Coverage Visualization
```bash
/test-deep all --report coverage.html
```

Generates HTML report showing:
- Code coverage heatmap
- Untested edge cases
- Provider comparison charts
- Performance graphs
- Quality trend lines

## Test Data Management

### Generating Test Fixtures
```python
# Auto-generated by test-deep
TEST_FIXTURES = {
    "simple": "She went to the store.",
    "complex": "She told him that they were her friends.",
    "ambiguous": "Alex helped Sam with their project.",
    "historical": "Lady Catherine and Sir William attended.",
    "dialogue": '"I am fine," she said to him.',
}
```

### Golden Test Sets
Maintains verified test cases:
```
tests/golden/
  ├── pride_prejudice_ch1.json
  ├── expected_output_ch1.json
  ├── edge_cases.json
  └── regression_baseline.json
```

## Success Metrics

Test suite ensures:
- **Accuracy**: >95% correct transformations
- **Consistency**: >90% provider agreement
- **Performance**: <5s for average book
- **Quality**: >85% readability preserved
- **Coverage**: >80% code coverage
- **Reliability**: <0.1% failure rate