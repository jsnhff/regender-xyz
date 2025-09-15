# Claude Code Commands for Regender-XYZ

Powerful commands that orchestrate specialized agents to refactor, build features, test, and improve the regender-xyz codebase.

## Quick Start

```bash
# Refactor for better architecture
/refactor architecture

# Build a new feature
/feature "Add batch processing with progress bars"

# Deep test with analysis
/test-deep transformation --verbose

# Review code changes
/review --fix

# Simplify complex code
/simplify all

# Profile performance
/profile bottlenecks --optimize

# Enhance CLI experience
/cli-ux improve --interactive
```

## Available Commands

### 🔧 `/refactor` - Intelligent Refactoring
Refactor code using multiple specialized agents for improved architecture, performance, and maintainability.

**Key Features:**
- Architecture analysis and improvement
- Performance optimization
- Complexity reduction
- Python 3.12+ modernization
- Service-specific refactoring

**Example:**
```bash
/refactor performance --metrics
```

### 🚀 `/feature` - Feature Development
Build complete features from concept to deployment using the full agent team.

**Key Features:**
- Parallel planning with PM, UX, and engineering
- Test-first development option
- Interactive planning sessions
- Multiple feature types (CLI, API, transform, provider)

**Example:**
```bash
/feature "Add interactive book selection" --type cli
```

### 🧪 `/test-deep` - Comprehensive Testing
Deep testing with analysis of results, edge cases, and quality metrics.

**Key Features:**
- Transformation accuracy testing
- Provider consistency comparison
- Edge case coverage
- Performance benchmarking
- Quality regression detection

**Example:**
```bash
/test-deep transformation --verbose --report
```

### 🔍 `/review` - Multi-Perspective Code Review
Comprehensive code review using multiple specialized agents.

**Key Features:**
- Security-focused reviews
- Performance analysis
- Auto-fix simple issues
- Comparative reviews
- Priority-based feedback

**Example:**
```bash
/review --fix --suggest
```

### ✨ `/simplify` - Complexity Reduction
Reduce complexity and improve code clarity across the codebase.

**Key Features:**
- Complex function breakdown
- Duplicate code elimination
- Import organization
- Type hint simplification
- Test structure improvement

**Example:**
```bash
/simplify complex --threshold 10
```

### 📊 `/profile` - Performance Profiling
Deep performance profiling with optimization recommendations.

**Key Features:**
- Bottleneck identification
- Provider comparison
- Memory usage analysis
- Auto-optimization mode
- Continuous monitoring

**Example:**
```bash
/profile bottlenecks --optimize
```

### 🎨 `/cli-ux` - CLI Experience Design
Design and implement exceptional command-line user experiences.

**Key Features:**
- Interactive mode design
- Progress indicators
- Error message enhancement
- Output formatting
- Shell completion

**Example:**
```bash
/cli-ux design interactive-transform
```

## Command Patterns

### Parallel Agent Execution
Commands use parallel agents for speed:
```yaml
# Planning phase runs 3 agents simultaneously
Phase 1 (Parallel):
  - product-manager: Requirements
  - ux-designer: Interface design
  - backend-specialist: Architecture
```

### Sequential Handoffs
Dependent tasks chain in sequence:
```yaml
# Implementation flows through review
Phase 2 (Sequential):
  - senior-software-engineer: Build
  - code-reviewer: Review
  - qa-specialist: Test
```

### Context Isolation
Each agent gets dedicated context:
- 200k token window per agent
- No cross-contamination
- Focused analysis

## Common Workflows

### Add New Feature
```bash
# Complete feature development workflow
/feature "Add streaming output" --test-first
/review
/test-deep all
```

### Refactor Service
```bash
# Comprehensive service refactoring
/refactor service character_service
/simplify complex
/profile service character_service
/test-deep regression
```

### Performance Optimization
```bash
# Find and fix bottlenecks
/profile bottlenecks
/refactor performance --focus "identified_bottlenecks"
/profile --compare baseline.json
```

### CLI Enhancement
```bash
# Improve user experience
/cli-ux improve --interactive --progress
/test-deep edge-cases
/review file regender_cli.py
```

## Options Reference

### Global Options
- `--dry-run` - Preview without applying changes
- `--verbose` - Detailed output
- `--fix` - Auto-fix issues when possible
- `--report` - Generate detailed reports
- `--iterate` - Multiple refinement passes

### Output Formats
- `text` - Human-readable (default)
- `json` - Machine-readable
- `html` - Interactive reports
- `diff` - Show changes

### Severity Levels
- `blockers` - Must fix before merge
- `high` - Strongly recommend fixing
- `medium` - Consider for follow-up
- `suggestions` - Nice to have

## Integration with Development

### Pre-Commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
claude-code /review changes --fix
claude-code /test-deep changes
```

### CI/CD Pipeline
```yaml
# .github/workflows/claude.yml
- name: Review Code
  run: claude-code /review --strict

- name: Test Quality
  run: claude-code /test-deep all --threshold 0.95

- name: Profile Performance
  run: claude-code /profile --baseline main
```

### Interactive Development
```bash
# Watch mode for continuous improvement
claude-code /review --watch
claude-code /simplify --watch
```

## Best Practices

1. **Start with Analysis**
   ```bash
   /refactor architecture --dry-run
   ```

2. **Use Test-First for Features**
   ```bash
   /feature "New capability" --test-first
   ```

3. **Profile Before Optimizing**
   ```bash
   /profile all --metrics
   ```

4. **Review Before Committing**
   ```bash
   /review changes --fix
   ```

5. **Simplify Regularly**
   ```bash
   /simplify all --threshold 10
   ```

## Metrics and Reports

Commands track and report:
- **Code Quality**: Complexity, duplication, coverage
- **Performance**: Speed, memory, token usage
- **UX Quality**: Response time, error clarity
- **Test Coverage**: Unit, integration, edge cases
- **Cost Efficiency**: Token usage, API costs

## Troubleshooting

### Command Not Found
Ensure `.claude/commands/` directory exists with command markdown files.

### Agent Timeout
Break large tasks into smaller scopes or increase timeout.

### Quality Regression
Use `/test-deep regression` to identify issues, then `/refactor` to fix.

### Performance Issues
Run `/profile bottlenecks` to identify, then `/refactor performance` to optimize.

## Contributing

To add new commands:
1. Create markdown file in `.claude/commands/`
2. Define workflow pattern with agents
3. Include examples and options
4. Test with real scenarios
5. Document integration points

## Future Commands

Planned additions:
- `/migrate` - Database and API migrations
- `/security` - Security audit and fixes
- `/document` - Auto-generate documentation
- `/deploy` - Deployment automation
- `/monitor` - Production monitoring setup