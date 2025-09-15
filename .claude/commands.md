# Claude Code Agent Commands

This file defines custom commands for Claude Code to orchestrate development agents in the regender-xyz project.

## Core Agent Commands

### `/architect` - Architecture Analysis Agent
Analyzes codebase architecture, identifies patterns, and suggests improvements.

**Usage:**
```
/architect [--scope <module|service|full>] [--focus <area>]
```

**Options:**
- `--scope`: Analysis scope (module, service, or full codebase)
- `--focus`: Specific area to focus on (e.g., "services", "providers", "strategies")

**Example:**
```
/architect --scope full
/architect --focus services
```

**Agent Behavior:**
- Analyzes module dependencies and coupling
- Identifies design patterns and anti-patterns
- Suggests architectural improvements
- Generates dependency graphs
- Reports on code organization

---

### `/engineer` - Senior Software Engineer Agent
Implements features, fixes bugs, and performs refactoring with best practices.

**Usage:**
```
/engineer <task-type> [--description "<task>"] [--files <file1,file2>]
```

**Task Types:**
- `feature`: Implement new functionality
- `bugfix`: Fix identified bugs
- `refactor`: Improve code quality
- `optimize`: Enhance performance

**Example:**
```
/engineer feature --description "Add caching to character service"
/engineer bugfix --files src/services/transform_service.py
/engineer refactor --files src/strategies/
```

**Agent Behavior:**
- Implements code following Python 3.12+ best practices
- Generates comprehensive tests
- Ensures proper error handling
- Documents changes
- Follows existing code patterns

---

### `/reviewer` - Code Review Agent
Reviews code for quality, security, and best practices.

**Usage:**
```
/reviewer [--files <file1,file2>] [--strict] [--focus <security|performance|style>]
```

**Options:**
- `--files`: Specific files to review (defaults to recent changes)
- `--strict`: Apply stricter review criteria
- `--focus`: Focus area for review

**Example:**
```
/reviewer --files src/services/
/reviewer --strict --focus security
```

**Agent Behavior:**
- Checks code style and conventions
- Identifies security vulnerabilities
- Evaluates error handling
- Assesses performance implications
- Provides actionable feedback with severity levels

---

### `/test` - Test Runner Agent
Executes tests and analyzes coverage.

**Usage:**
```
/test [--type <unit|integration|coverage|all>] [--files <file1,file2>]
```

**Options:**
- `--type`: Type of tests to run
- `--files`: Specific files to test

**Example:**
```
/test --type all
/test --type unit --files src/services/character_service.py
```

**Agent Behavior:**
- Runs pytest with detailed reporting
- Analyzes test coverage
- Identifies missing tests
- Suggests test improvements
- Reports test metrics

---

### `/refactor` - Refactoring Specialist Agent
Performs targeted code refactoring for improved quality.

**Usage:**
```
/refactor <pattern> [--files <file1,file2>] [--preview]
```

**Patterns:**
- `extract-method`: Extract complex logic
- `reduce-coupling`: Minimize dependencies
- `improve-naming`: Better variable/function names
- `add-types`: Add type hints
- `modernize`: Update to Python 3.12+ features

**Example:**
```
/refactor modernize --files src/
/refactor add-types --preview
```

---

### `/quality` - Quality Assurance Agent
Comprehensive quality checks and improvements.

**Usage:**
```
/quality [--check <all|security|performance|docs>] [--fix]
```

**Options:**
- `--check`: Type of quality check
- `--fix`: Attempt automatic fixes

**Example:**
```
/quality --check all
/quality --check security --fix
```

---

## Workflow Commands

### `/workflow` - Execute Complete Workflows
Orchestrates multiple agents for complex tasks.

**Usage:**
```
/workflow <workflow-type> [--description "<task>"] [--iterations <n>]
```

**Workflow Types:**
- `feature`: Full feature development (architect → engineer → reviewer → test)
- `bugfix`: Bug fixing workflow (engineer → test → reviewer)
- `refactor`: Refactoring workflow (architect → refactor → test → reviewer)
- `review`: Code review workflow
- `pipeline`: Full development pipeline with iterations

**Example:**
```
/workflow feature --description "Add user authentication"
/workflow refactor --iterations 2
/workflow pipeline --description "Optimize performance"
```

**Agent Behavior:**
- Executes agents in optimal sequence
- Passes context between agents
- Handles iterative refinement
- Aggregates results from all agents
- Provides comprehensive final report

---

### `/parallel` - Parallel Agent Execution
Run multiple independent agents concurrently.

**Usage:**
```
/parallel <agent1,agent2,...> [--context <shared-context>]
```

**Example:**
```
/parallel architect,test --context "Analyze and test current state"
/parallel reviewer,quality
```

---

## Quick Commands

### `/quick-review`
Quick code review of recent changes.
```
/quick-review
```

### `/quick-test`
Run tests for recently modified files.
```
/quick-test
```

### `/quick-fix`
Identify and fix common issues.
```
/quick-fix
```

---

## Custom Agent Definitions

### Creating Custom Agents
You can define custom agents by creating a YAML configuration:

```yaml
name: custom-agent
description: "Custom agent for specific task"
model: opus  # opus, sonnet, or haiku
context_limit: 200000
parallel: true
tools:
  - ast_analysis
  - code_generation
workflow:
  - step: analyze
    action: "Analyze the codebase"
  - step: implement
    action: "Implement changes"
  - step: validate
    action: "Validate results"
```

---

## Advanced Usage

### Chaining Commands
Chain multiple commands for complex operations:
```
/architect --scope full && /engineer refactor --files src/services/ && /test --type all
```

### Conditional Execution
Execute based on previous results:
```
/reviewer --strict || /engineer bugfix --description "Fix review issues"
```

### Saving Results
Save agent results to file:
```
/workflow feature --description "New feature" > results.json
```

---

## Best Practices

1. **Start with Architecture Review**: Run `/architect` before major changes
2. **Use Workflows for Complex Tasks**: Leverage `/workflow` for multi-step operations
3. **Parallel When Possible**: Use `/parallel` for independent tasks
4. **Iterate with Feedback**: Use `--iterations` for refinement
5. **Review Before Commit**: Always run `/reviewer` before committing
6. **Test Coverage**: Ensure `/test --type coverage` shows >80%

---

## Environment Variables

Set these for optimal agent performance:

```bash
export AGENT_MODEL=opus           # Default model
export AGENT_VERBOSE=true         # Detailed output
export AGENT_MAX_RETRIES=3        # Retry failed operations
export AGENT_TIMEOUT=300          # Timeout in seconds
export AGENT_PARALLEL_LIMIT=4     # Max parallel agents
```

---

## Troubleshooting

### Agent Failures
If an agent fails, check:
1. Context requirements are met
2. Required tools are available
3. File paths are correct
4. Dependencies are installed

### Performance Issues
For better performance:
1. Use `sonnet` model for simpler tasks
2. Limit context with specific file targets
3. Use parallel execution when possible
4. Cache results between iterations

---

## Integration with CI/CD

Add to your CI pipeline:

```yaml
# .github/workflows/agents.yml
- name: Architecture Review
  run: claude-code /architect --scope full

- name: Code Quality
  run: claude-code /quality --check all

- name: Test Coverage
  run: claude-code /test --type coverage
```