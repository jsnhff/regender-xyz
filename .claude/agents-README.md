# Claude Code Agents for Regender-XYZ

This directory contains specialized AI agents for the regender-xyz project, designed to work with Claude Code for development, testing, and maintenance tasks.

## Agent Architecture

Based on three core principles:
1. **Parallel Execution for Speed** - Independent agents run concurrently
2. **Sequential Handoffs for Automation** - Dependent agents chain in sequence
3. **Context Isolation for Quality** - Each agent gets dedicated context window

## Available Agents

### Core Development Agents

#### 🎯 `product-manager`
Transforms high-level requirements into detailed specifications.
- Creates PRDs and user stories
- Defines acceptance criteria
- Manages feature scope

#### 🎨 `ux-designer`
Designs user experiences and interaction patterns.
- Creates user flows and states
- Ensures accessibility
- Designs CLI interactions

#### 💻 `senior-software-engineer`
Implements features with best practices.
- Writes production code
- Creates comprehensive tests
- Follows Python 3.12+ patterns

#### 🔍 `code-reviewer`
Reviews code for quality and security.
- Checks correctness and clarity
- Identifies security issues
- Suggests improvements

### Specialized Agents

#### ⚙️ `backend-specialist`
Expert in LLM integrations and text processing.
- Optimizes provider integrations
- Implements rate limiting
- Manages token chunking

#### ✅ `qa-specialist`
Ensures quality through comprehensive testing.
- Designs test strategies
- Validates transformations
- Tracks quality metrics

#### 📚 `docs-specialist`
Creates clear technical documentation.
- API documentation
- Architecture guides
- Usage examples

#### 🔄 `feature-workflow`
Orchestrates multi-agent workflows.
- Manages parallel execution
- Handles sequential handoffs
- Combines agent outputs

## Usage Examples

### Basic Agent Invocation

```bash
# Use a single agent
Task(senior-software-engineer, "Implement caching for character analysis")

# Parallel execution
Task(product-manager, "Define batch processing requirements") &
Task(backend-specialist, "Design batch architecture") &
Task(qa-specialist, "Create batch processing test plan")

# Sequential workflow
Task(senior-software-engineer, "Implement feature") ->
Task(code-reviewer, "Review implementation") ->
Task(qa-specialist, "Validate quality")
```

### Common Workflows

#### Feature Development
```yaml
Phase 1 (Parallel):
  - product-manager: Requirements
  - ux-designer: User experience
  - backend-specialist: Technical design

Phase 2 (Sequential):
  - senior-software-engineer: Implementation
  - code-reviewer: Review
  - qa-specialist: Testing
```

#### Bug Fix
```yaml
Sequential:
  - senior-software-engineer: Fix bug
  - qa-specialist: Test fix
  - code-reviewer: Review changes
```

#### Performance Optimization
```yaml
Phase 1 (Parallel):
  - backend-specialist: Profile bottlenecks
  - qa-specialist: Establish baselines

Phase 2 (Sequential):
  - senior-software-engineer: Optimize
  - qa-specialist: Verify improvements
```

## Agent Capabilities

### Product Manager
- Startup-focused pragmatic approach
- Automatic ticket breakdown for >2 day tasks
- MVP-first methodology
- 80/20 rule application

### Senior Software Engineer
- Service-oriented architecture expertise
- Strategy pattern implementation
- Async/await patterns
- Comprehensive error handling

### Backend Specialist
- Multi-provider LLM management
- Token counting and chunking
- Rate limiting strategies
- Performance optimization

### Code Reviewer
- Security vulnerability detection
- Architecture pattern validation
- Performance issue identification
- Constructive feedback

### QA Specialist
- Transformation validation
- Edge case testing
- Regression detection
- Quality metrics tracking

## Configuration

Agents can be configured through environment variables:

```bash
# Agent model selection
export AGENT_MODEL=opus  # opus, sonnet, or haiku

# Execution settings
export AGENT_PARALLEL_LIMIT=4
export AGENT_TIMEOUT=300
export AGENT_MAX_RETRIES=3

# Verbosity
export AGENT_VERBOSE=true
```

## Best Practices

### When to Use Parallel Execution
- Independent analysis tasks
- Multiple perspective gathering
- Non-blocking operations
- Initial research phases

### When to Use Sequential Handoffs
- Implementation followed by review
- Testing after development
- Documentation after implementation
- Iterative refinement

### Context Management
- Keep contexts focused and relevant
- Pass only necessary information between agents
- Document context requirements
- Monitor context usage

## Integration with Regender-XYZ

### Service Architecture
All agents understand and work with:
- Service-oriented patterns in `src/services/`
- Strategy patterns in `src/strategies/`
- Provider abstractions in `src/providers/`
- Dependency injection via `src/container.py`

### Code Standards
Agents enforce:
- Python 3.12+ features
- Ruff compliance
- Type hints
- >80% test coverage
- Async/await patterns

### Common Tasks
Agents can handle:
- Adding new transformation types
- Integrating new LLM providers
- Optimizing performance
- Improving quality validation
- Extending CLI functionality

## Troubleshooting

### Agent Not Found
Ensure agent markdown file exists in `.claude/agents/`

### Context Overflow
Break task into smaller subtasks or use sequential handoffs

### Parallel Execution Issues
Check for dependencies between agents that should run sequentially

### Quality Issues
Use qa-specialist to validate outputs and establish quality gates

## Contributing

To add a new agent:

1. Create markdown file in `.claude/agents/`
2. Define agent mission and responsibilities
3. Specify operating principles
4. Include domain-specific examples
5. Document integration points

## Future Enhancements

- [ ] Add metrics tracking for agent performance
- [ ] Implement agent learning from feedback
- [ ] Create specialized agents for specific domains
- [ ] Build agent composition patterns
- [ ] Add agent testing framework