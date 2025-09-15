# /feature

Build new features from concept to deployment using the full agent team.

## Usage

```bash
/feature <description> [options]
```

## Options

- `--type <type>` - Feature type: `cli`, `api`, `transform`, `provider`, `optimization`
- `--priority <level>` - `mvp`, `standard`, `complete`
- `--test-first` - TDD approach
- `--interactive` - Interactive planning session

## Workflow Pattern

### Phase 1: Planning Sprint (Parallel)
```yaml
Agents:
  - product-manager: Define requirements and success criteria
  - ux-designer: Design CLI interactions and output formats
  - backend-specialist: Architect technical solution

Duration: ~2 minutes
Output: Complete feature specification
```

### Phase 2: Implementation (Sequential)
```yaml
Agents:
  - senior-software-engineer: Implement with tests
  - code-reviewer: Review and suggest improvements
  If improvements needed:
    - senior-software-engineer: Apply feedback

Duration: ~5 minutes
Output: Production-ready code
```

### Phase 3: Quality & Polish (Parallel)
```yaml
Agents:
  - qa-specialist: Run comprehensive tests
  - docs-specialist: Create documentation
  - ux-designer: Validate CLI experience

Duration: ~2 minutes
Output: Tested, documented feature
```

## Feature Types

### CLI Enhancement
```bash
/feature "Add interactive mode for selecting books to transform" --type cli
```
Creates:
- Interactive prompts using rich/click
- Arrow key navigation
- Preview before confirmation
- Progress indicators

### New Transformation
```bash
/feature "Add historical period gender norms transformation" --type transform
```
Creates:
- New transformation strategy
- Period-specific rules engine
- Configuration options
- Quality validation

### Provider Integration
```bash
/feature "Add Ollama local LLM support" --type provider
```
Creates:
- Provider implementation
- Rate limiting strategy
- Fallback handling
- Configuration

### Performance Feature
```bash
/feature "Add parallel book processing" --type optimization
```
Creates:
- Async batch processing
- Progress tracking
- Resource management
- Error recovery

## Example Features for Regender-XYZ

### 1. Interactive Book Selection
```bash
/feature "Interactive book selection with preview" --type cli --priority mvp
```

Expected output:
```python
$ regender --interactive
? Select books to transform: (Use arrow keys)
 ❯ ◉ Pride and Prejudice (pg1342.txt)
   ◯ Alice in Wonderland (pg11.txt)
   ◯ Sherlock Holmes (pg1661.txt)

? Select transformation:
 ❯ Gender Swap
   All Female
   All Male
   Non-Binary

? Preview first paragraph? (Y/n)
```

### 2. Batch Processing with Resume
```bash
/feature "Batch processing with checkpoint resume" --test-first
```

Creates capability for:
```bash
$ regender batch books/*.txt --checkpoint
Processing 10 books...
[████████--] 8/10 Complete

# If interrupted, resume from checkpoint
$ regender batch --resume
Resuming from book 9/10...
```

### 3. Diff View for Transformations
```bash
/feature "Show side-by-side diff of transformations" --type cli
```

Creates:
```bash
$ regender book.txt gender_swap --diff
Original                    | Transformed
---------------------------|---------------------------
She walked into the room   | He walked into the room
and greeted her friends.   | and greeted his friends.
```

### 4. Configuration Profiles
```bash
/feature "Save and load transformation profiles" --priority complete
```

Enables:
```bash
$ regender --save-profile victorian
Profile 'victorian' saved

$ regender book.txt --profile victorian
Loading profile 'victorian'...
```

### 5. Real-time Streaming Output
```bash
/feature "Stream transformation output as it processes" --type cli
```

Creates live output:
```bash
$ regender large_book.txt gender_swap --stream
Chapter 1: The Beginning [✓]
Chapter 2: The Journey [processing...]
  └─ Paragraph 42 of 156
```

## Success Criteria

Every feature includes:
- ✅ Complete implementation with error handling
- ✅ Comprehensive test coverage (>80%)
- ✅ CLI help text and examples
- ✅ Documentation with usage patterns
- ✅ Performance benchmarks
- ✅ Backward compatibility

## Integration Patterns

### With Existing Services
```python
# New features integrate with service architecture
class NewFeatureService(BaseService):
    def __init__(self, parser_service, character_service):
        self.parser = parser_service
        self.character = character_service
```

### CLI Integration
```python
# Add to regender_cli.py
@click.command()
@click.option('--new-feature', help='Enable new feature')
def transform(new_feature):
    if new_feature:
        service.enable_feature('new_feature')
```

## Testing Strategy

Each feature includes:
1. **Unit tests** - Component isolation
2. **Integration tests** - Service interaction
3. **CLI tests** - Command-line interface
4. **Performance tests** - Speed and memory
5. **Edge case tests** - Unusual inputs

## Documentation Output

Each feature generates:
- README section
- CLI help text
- Code examples
- API documentation
- Migration guide (if breaking changes)