# /review

Comprehensive code review using multiple perspectives to ensure quality, security, and maintainability.

## Usage

```bash
/review [scope] [options]
```

## Scopes

- `changes` - Review recent changes (default)
- `pr` - Review pull request
- `file <path>` - Review specific file
- `service <name>` - Review entire service
- `security` - Security-focused review
- `performance` - Performance-focused review

## Options

- `--strict` - Apply stricter review criteria
- `--fix` - Auto-fix simple issues
- `--suggest` - Generate improvement suggestions
- `--compare <branch>` - Review against branch

## Workflow Pattern

### Phase 1: Multi-Perspective Analysis (Parallel)
```yaml
Agents:
  - code-reviewer: General code quality and patterns
  - backend-specialist: Architecture and performance
  - qa-specialist: Test coverage and edge cases
  - ux-designer: CLI usability and output

Output: Comprehensive review from all angles
```

### Phase 2: Prioritization (Sequential)
```yaml
Agent:
  - code-reviewer: Synthesize and prioritize findings

Output: Categorized issues by severity
```

### Phase 3: Remediation (Optional)
```yaml
If --fix flag:
  - senior-software-engineer: Apply automatic fixes
  - qa-specialist: Verify fixes don't break tests

Output: Fixed code with explanations
```

## Review Categories

### Standard Code Review
```bash
/review
```

Output format:
```
=== CODE REVIEW REPORT ===

Summary: NEEDS REVISION
- Blockers: 2
- High Priority: 3
- Suggestions: 8

🚫 BLOCKERS (Must Fix)
------------------------
1. [security] Hardcoded API key in config.py:47
   Fix: Use environment variable

2. [logic] Race condition in async character processing
   File: services/character_service.py:234
   Fix: Add proper locking mechanism

⚠️ HIGH PRIORITY
------------------------
1. [performance] N+1 query pattern in book processing
   Impact: 10x slower for large books
   Fix: Batch character lookups

2. [error-handling] Unhandled LLM timeout
   File: providers/openai_provider.py:89
   Fix: Add timeout handling with retry

💡 SUGGESTIONS
------------------------
1. [clarity] Complex function could be split
   File: transform_service.py:145-203
   Suggestion: Extract transformation logic

✅ GOOD PRACTICES
------------------------
- Excellent async/await usage
- Comprehensive error messages
- Good test coverage (84%)
```

### Security Review
```bash
/review security --strict
```

Focuses on:
- API key handling
- Input validation
- Command injection risks
- Dependency vulnerabilities
- Data sanitization

### Performance Review
```bash
/review performance --suggest
```

Analyzes:
- Algorithmic complexity
- Memory usage patterns
- Async bottlenecks
- Caching opportunities
- Database queries

## Specific Review Patterns for Regender-XYZ

### Provider Implementation Review
```bash
/review file src/providers/new_provider.py
```

Checks:
- Rate limiting implementation
- Error handling completeness
- Token counting accuracy
- Fallback mechanisms
- Cost optimization

### Transformation Logic Review
```bash
/review service transform_service
```

Validates:
- Pronoun consistency logic
- Context preservation
- Edge case handling
- Performance optimization
- Test coverage

### CLI Interface Review
```bash
/review file regender_cli.py --suggest
```

Evaluates:
- Command structure clarity
- Help text quality
- Error message helpfulness
- Output format options
- Progress indicators

## Auto-Fix Capabilities

```bash
/review --fix
```

Automatically fixes:
- Import sorting
- Whitespace issues
- Simple type hints
- Obvious variable names
- Basic docstrings
- Ruff violations

Example:
```python
# Before
def process(x,y):
    return x+y

# After (auto-fixed)
def process(x: int, y: int) -> int:
    """Process two integers.

    Args:
        x: First integer
        y: Second integer

    Returns:
        Sum of x and y
    """
    return x + y
```

## Review Comparison

```bash
/review --compare main
```

Shows what changed:
```
=== Review Comparison: feature-branch vs main ===

New Issues Introduced:
- 2 performance regressions
- 1 missing test case

Issues Fixed:
- 3 type hint issues resolved
- 2 error handling improvements

Code Quality Metrics:
- Complexity: 4.2 → 3.8 (improved)
- Test Coverage: 82% → 84% (improved)
- Type Coverage: 76% → 89% (improved)
```

## Integration with Development Flow

### Pre-Commit Review
```bash
# Add to .git/hooks/pre-commit
/review changes --fix
```

### PR Review
```bash
/review pr --strict
```

### Continuous Review
```bash
# Review as you code
/review --watch
```

## Review Metrics

Tracks and reports:
- **Issue Density**: Issues per 100 lines
- **Fix Rate**: % of issues auto-fixed
- **Review Time**: Time to complete review
- **Quality Trend**: Improvement over time
- **Coverage Delta**: Test coverage change

## Custom Review Rules

Create `.claude/review-rules.yaml`:
```yaml
rules:
  - name: "No print statements"
    pattern: "print\\("
    severity: "high"
    message: "Use logging instead of print"

  - name: "Async function naming"
    pattern: "async def (?!.*async)"
    severity: "suggestion"
    message: "Consider adding 'async' to function name"

  - name: "Token limit check"
    pattern: "provider\\.complete\\("
    requires: "count_tokens"
    severity: "high"
    message: "Always check token count before LLM call"
```

## Review Reports

### Generate HTML Report
```bash
/review service all --report review.html
```

Creates interactive report with:
- Code quality dashboard
- Issue breakdown by category
- Trend graphs
- File heatmap
- Suggested fix priority

### Generate PR Comment
```bash
/review pr --format github
```

Creates GitHub-formatted comment:
```markdown
## 🔍 Code Review Results

**Verdict**: NEEDS REVISION

### 🚫 Blockers (2)
- [ ] Fix hardcoded API key in config.py
- [ ] Resolve race condition in character processing

### ⚠️ High Priority (3)
- [ ] Optimize N+1 query pattern
- [ ] Add timeout handling
- [ ] Improve error messages

### ✅ Positive Notes
- Great test coverage improvement
- Clean async implementation
```