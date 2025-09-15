# /refactor

Intelligently refactor code using multiple specialized agents to improve architecture, performance, and maintainability.

## Usage

```bash
/refactor <scope> [options]
```

## Scopes

- `architecture` - Analyze and improve system architecture
- `performance` - Optimize for speed and efficiency
- `simplify` - Reduce complexity and improve readability
- `modernize` - Update to Python 3.12+ patterns
- `service <name>` - Refactor specific service
- `all` - Comprehensive refactoring

## Options

- `--dry-run` - Preview changes without applying
- `--focus <area>` - Target specific area (e.g., "providers", "strategies")
- `--metrics` - Show before/after metrics
- `--iterate` - Multiple refinement passes

## Workflow Pattern

### Phase 1: Analysis (Parallel)
```yaml
Agents:
  - backend-specialist: Analyze current architecture and bottlenecks
  - qa-specialist: Identify test coverage gaps and quality issues
  - code-reviewer: Find code smells and anti-patterns

Output: Comprehensive refactoring plan with priorities
```

### Phase 2: Implementation (Sequential)
```yaml
Agents:
  - senior-software-engineer: Apply refactoring based on analysis
  - code-reviewer: Review changes for correctness
  - qa-specialist: Ensure no regressions

Output: Refactored code with tests
```

### Phase 3: Validation (Parallel)
```yaml
Agents:
  - qa-specialist: Run comprehensive tests
  - backend-specialist: Verify performance improvements
  - docs-specialist: Update documentation

Output: Validated refactoring with metrics
```

## Examples

### Refactor Architecture
```bash
/refactor architecture --focus services
```
Analyzes service coupling, suggests dependency injection improvements, and implements cleaner separation of concerns.

### Optimize Performance
```bash
/refactor performance --metrics
```
Profiles code, identifies bottlenecks, implements caching, async improvements, and shows before/after metrics.

### Simplify Complex Code
```bash
/refactor simplify --focus "src/services/transform_service.py"
```
Breaks down complex functions, improves naming, reduces cyclomatic complexity.

### Modernize to Python 3.12+
```bash
/refactor modernize
```
Updates code to use modern Python features: type hints, dataclasses, match/case, walrus operator, etc.

### Comprehensive Service Refactor
```bash
/refactor service character_service --iterate
```
Complete refactoring of a service with multiple improvement passes.

## Specific Refactoring Patterns

### Token Management Optimization
```bash
/refactor performance --focus "token_counting"
```
- Implement smart chunking strategies
- Add caching for token counts
- Optimize context window usage

### Provider Abstraction Improvement
```bash
/refactor architecture --focus "providers"
```
- Standardize provider interfaces
- Implement better fallback mechanisms
- Add provider-specific optimizations

### Test Coverage Enhancement
```bash
/refactor simplify --focus "tests" --metrics
```
- Simplify test setup with better fixtures
- Add missing edge cases
- Improve test organization

## Success Metrics

The command tracks and reports:
- **Complexity Reduction**: Cyclomatic complexity decrease
- **Performance Gains**: Speed improvements, memory usage
- **Test Coverage**: Coverage percentage increase
- **Code Quality**: Linting scores, type coverage
- **Maintainability**: Coupling metrics, cohesion scores

## Integration Points

Works seamlessly with:
- `/test` - Validates refactoring
- `/review` - Ensures quality
- `/profile` - Measures improvements
- `/document` - Updates docs

## Error Handling

- Automatic rollback on test failures
- Incremental refactoring with checkpoints
- Clear reporting of what changed and why
- Git-friendly atomic commits