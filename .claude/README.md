# Ultra-Simple Claude Code Agent System

## Philosophy: 2 Agents, 0 Commands

We've radically simplified from 8 agents + 7 commands to just **2 agents** that cover everything:

### 🔧 `engineer` Agent
**Everything code-related**
- Build features and fix bugs
- Review code quality and security
- Write tests and validate quality
- Profile performance and optimize

**Usage:**
```bash
# Just ask for what you need
"Add batch processing to handle multiple books"
"Fix the memory leak in character analysis"
"Optimize the transformation service"
"Review and improve the parser code"
```

### 📝 `product` Agent
**Everything user-related**
- Plan features and define requirements
- Design CLI UX and user flows
- Write documentation and guides
- Analyze usage and improvements

**Usage:**
```bash
# Just describe what you want
"Plan a feature for interactive character selection"
"Improve the error messages to be more helpful"
"Document how the transformation service works"
"Design better progress indication for long operations"
```

## Why This Works Better

### Before (Complex)
- 8 specialized agents with overlapping roles
- 7 commands orchestrating multiple agents
- Complex parallel/sequential workflows
- High token usage (200k × multiple agents)
- Cognitive overhead choosing agents/commands

### After (Simple)
- 2 clear agents with distinct purposes
- No commands needed - just describe tasks
- Natural language requests
- Efficient token usage
- Zero learning curve

## How to Use

### For Code Tasks → Use `engineer`
```bash
Task(engineer, "implement rate limiting for the OpenAI provider")
Task(engineer, "fix the failing tests in test_character_service.py")
Task(engineer, "refactor the parser to reduce complexity")
Task(engineer, "profile and optimize book processing performance")
```

### For Product Tasks → Use `product`
```bash
Task(product, "design a better onboarding experience for new users")
Task(product, "write a guide for adding new transformation types")
Task(product, "plan batch processing feature with progress bars")
Task(product, "improve error messages throughout the CLI")
```

### For Mixed Tasks → Use Both (Rarely Needed)
```bash
# Parallel when truly independent
Task(product, "define requirements for streaming output")
Task(engineer, "research streaming implementation options")

# Sequential when one depends on other
Task(product, "design the UX for book selection") →
Task(engineer, "implement the book selection feature")
```

## Examples

### Adding a Feature
```bash
# Option 1: Engineer figures it out
Task(engineer, "add interactive book selection with arrow keys")

# Option 2: Product plans first (if complex)
Task(product, "design interactive book selection flow")
# Then...
Task(engineer, "implement the design from product agent")
```

### Fixing a Bug
```bash
Task(engineer, "fix: character names with apostrophes break parsing")
```

### Improving Performance
```bash
Task(engineer, "make book processing 2x faster")
```

### Better UX
```bash
Task(product, "make error messages helpful with recovery suggestions")
```

## Decision Tree

```
Is it about code? → engineer
Is it about users/docs? → product
Not sure? → Start with one, it'll tell you if you need the other
```

## Benefits

1. **Simplicity**: 2 agents cover everything
2. **Flexibility**: Natural language, no rigid commands
3. **Efficiency**: Less orchestration overhead
4. **Clarity**: Clear separation of concerns
5. **Speed**: Direct execution, no multi-phase workflows

## Migration from Old System

| Old Command | New Approach |
|------------|--------------|
| `/refactor architecture` | `Task(engineer, "refactor the architecture for better modularity")` |
| `/feature "Add X"` | `Task(engineer, "add feature X")` or `Task(product, "plan feature X")` |
| `/test-deep` | `Task(engineer, "comprehensive testing with edge cases")` |
| `/review` | `Task(engineer, "review the code for quality and security")` |
| `/simplify` | `Task(engineer, "simplify complex code")` |
| `/profile` | `Task(engineer, "profile performance and optimize bottlenecks")` |
| `/cli-ux` | `Task(product, "improve CLI user experience")` |

## The Core Insight

**Most tasks don't need orchestration.** A capable agent can handle planning, implementation, and validation within their domain. Only truly complex, multi-domain tasks benefit from multiple agents, and even then, 2 is usually enough.

---

*Complexity is the enemy of reliability. Keep it simple.*