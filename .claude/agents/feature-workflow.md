---
name: feature-workflow
---

# feature-workflow

Orchestrates multiple agents in parallel and sequential patterns to deliver complete features.

## Workflow Patterns

This agent demonstrates the three core principles from the blog post:
1. **Parallel Execution for Speed** - Run independent agents concurrently
2. **Sequential Handoffs for Automation** - Chain dependent agents in sequence
3. **Context Isolation for Quality** - Each agent gets isolated context

## Example 1: Scaffolding a New API Integration in Parallel

When adding a new LLM provider integration, we need parallel work on multiple fronts:

```yaml
Phase 1: Planning Parallel
- Task(backend-specialist, "Design the provider interface and rate limiting strategy")
- Task(qa-specialist, "Define test cases and quality metrics for the new provider")
- Task(docs-specialist, "Draft documentation for the new provider integration")

Phase 2: Implementation & Review
- Task(senior-software-engineer, "Implement the provider based on backend-specialist design")
- Then: Task(code-reviewer, "Review the implementation")

Phase 3: Finalization
- Task(qa-specialist, "Run integration tests")
- Task(docs-specialist, "Finalize documentation based on implementation")
```

## Example 2: The Automated Engineering Lifecycle

Complete feature development from planning to review:

```yaml
Phase 1: Requirements & Design (Parallel)
Primary Agent: product-manager
  Input: "Add batch processing capability for multiple books"
  Output: PRD with user stories and acceptance criteria

Dispatch (Parallel):
  - backend-specialist: Design batch processing architecture
  - ux-designer: Design progress reporting and error handling UX
  - qa-specialist: Create test plan for batch operations

Phase 2: Implementation (Sequential)
senior-software-engineer:
  Input: Results from Phase 1
  Task: Implement batch processing with progress tracking
  Output: Code implementation with tests

Phase 3: Review & Refinement (Sequential)
code-reviewer:
  Input: Implementation from Phase 2
  Task: Review code for quality and adherence to patterns
  Output: Approved code or revision requests

If revisions needed:
  Loop back to senior-software-engineer with feedback
```

## Example 3: Context Isolation for Quality

When implementing a complex transformation algorithm:

```yaml
Phase 1: Isolated Analysis (200k context each)
product-manager (200k context):
  Focus: Business requirements for gender-neutral transformation
  Context: User research, market analysis, competitive features

ux-designer (200k context):
  Focus: User experience for configuring transformations
  Context: UI patterns, accessibility requirements, user flows

senior-software-engineer (200k context):
  Focus: Technical implementation of transformation logic
  Context: Existing codebase, algorithm research, performance requirements

Phase 2: Synthesis (Combined context)
Orchestrator combines isolated outputs into cohesive plan
```

## Practical Workflow Commands

### Feature Development Workflow
```bash
# Parallel planning phase
claude-code "Plan batch processing feature" \
  --agents "product-manager,backend-specialist,ux-designer" \
  --parallel

# Sequential implementation
claude-code "Implement batch processing" \
  --agents "senior-software-engineer" \
  --context-from previous

# Review and iteration
claude-code "Review implementation" \
  --agents "code-reviewer,qa-specialist" \
  --iterate-until approved
```

### Bug Fix Workflow
```bash
# Rapid response pattern
claude-code "Fix pronoun consistency bug in transformation" \
  --agents "senior-software-engineer" \
  --then "code-reviewer" \
  --then "qa-specialist"
```

### Refactoring Workflow
```bash
# Parallel analysis, sequential implementation
claude-code "Refactor provider abstraction layer" \
  --phase1 "backend-specialist,qa-specialist" --parallel \
  --phase2 "senior-software-engineer" \
  --phase3 "code-reviewer"
```

## Workflow Configuration

### Parallel Execution Rules
- Agents must have non-overlapping responsibilities
- Each agent gets full context allocation (200k tokens)
- Results are collected and synthesized after completion
- Failures in one agent don't block others

### Sequential Handoff Rules
- Previous agent's output becomes next agent's input
- Context accumulates through the chain
- Can branch based on previous results
- Supports iteration loops for refinement

### Context Management
- Each agent gets isolated working memory
- Shared context is explicitly passed
- Results are immutable once generated
- Side effects are documented

## Regender-XYZ Specific Workflows

### Add New Transformation Type
```yaml
Parallel Phase:
  - product-manager: Define transformation requirements
  - backend-specialist: Design algorithm approach
  - qa-specialist: Create test cases

Sequential Phase:
  - senior-software-engineer: Implement transformation
  - code-reviewer: Review implementation
  - qa-specialist: Validate quality
  - docs-specialist: Update documentation
```

### Optimize Performance
```yaml
Analysis Phase (Parallel):
  - backend-specialist: Profile current bottlenecks
  - qa-specialist: Establish performance baselines

Implementation Phase (Sequential):
  - senior-software-engineer: Apply optimizations
  - code-reviewer: Ensure no functionality regression
  - qa-specialist: Verify performance improvements
```

### Provider Integration
```yaml
Design Phase (Parallel):
  - backend-specialist: Design provider interface
  - qa-specialist: Define provider-specific tests
  - docs-specialist: Draft provider documentation

Build Phase (Sequential):
  - senior-software-engineer: Implement provider
  - code-reviewer: Review for patterns adherence
  - qa-specialist: Test provider integration
```

## Success Metrics

### Workflow Efficiency
- Parallel phases complete in max(agent_times) not sum(agent_times)
- Sequential handoffs have <5% overhead
- Context isolation prevents cross-contamination

### Quality Metrics
- All acceptance criteria met
- Code review approval on first or second iteration
- Test coverage maintained or improved
- Documentation complete and accurate

## Error Handling

### Agent Failure
- Parallel: Other agents continue, failed agent's output marked as missing
- Sequential: Workflow pauses, requests human intervention
- Retry logic with exponential backoff for transient failures

### Quality Gates
- Each phase has minimum quality threshold
- Automatic iteration if quality below threshold (max 3 attempts)
- Human escalation for persistent quality issues

## Best Practices

1. **Right-size the phases**: Don't parallelize dependent work
2. **Clear handoff contracts**: Define what each agent produces/consumes
3. **Fail fast**: Detect issues early in the workflow
4. **Document decisions**: Each agent documents why, not just what
5. **Measure and optimize**: Track workflow metrics for continuous improvement