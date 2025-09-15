# /cli-ux

Design and implement exceptional command-line user experiences.

## Usage

```bash
/cli-ux <task> [options]
```

## Tasks

- `improve` - Enhance existing CLI interface
- `design <feature>` - Design new CLI feature
- `interactive` - Add interactive modes
- `help` - Improve help and documentation
- `output` - Enhance output formatting
- `errors` - Improve error messages

## Options

- `--style <style>` - Output style (minimal|rich|verbose)
- `--colors` - Add color coding
- `--progress` - Add progress indicators
- `--examples` - Generate usage examples

## Workflow Pattern

### Phase 1: UX Analysis (Parallel)
```yaml
Agents:
  - ux-designer: Design CLI interactions
  - qa-specialist: Test user scenarios
  - docs-specialist: Create help text

Output: CLI design specification
```

### Phase 2: Implementation (Sequential)
```yaml
Agents:
  - senior-software-engineer: Implement CLI features
  - ux-designer: Validate implementation
  - qa-specialist: Test edge cases

Output: Enhanced CLI with tests
```

## CLI Enhancement Examples

### Interactive Mode
```bash
/cli-ux design interactive-transform
```

Creates rich interactive experience:
```bash
$ regender --interactive

╭─────────────────────────────────────────────╮
│         📚 Regender-XYZ v1.3.0             │
│     Transform Gender in Literature          │
╰─────────────────────────────────────────────╯

? What would you like to do?
  ❯ Transform a single book
    Batch process multiple books
    Download from Project Gutenberg
    View previous transformations
    Configure settings

? Select a book to transform:
  ❯ ◉ Pride and Prejudice (758 KB)
    ○ Alice in Wonderland (287 KB)
    ○ Sherlock Holmes (423 KB)
    ○ [Browse for file...]

? Choose transformation type:
  ❯ Gender Swap - Swap all gender representations
    All Female - Convert to female representation
    All Male - Convert to male representation
    Non-Binary - Use gender-neutral language
    Custom - Define custom rules

? Configuration options: (Press space to select)
  ◉ Preserve character names
  ◉ Show progress bar
  ○ Generate diff view
  ○ Verbose output
  ○ Save to profile

✓ Ready to transform!

  Book: Pride and Prejudice
  Type: Gender Swap
  Output: pride_prejudice_swapped.json

? Proceed? (Y/n) █
```

### Progress Indicators
```bash
/cli-ux improve --progress
```

Implements various progress styles:
```bash
# Simple progress bar
Processing book... ████████████████░░░░ 80% | 8/10 chapters

# Detailed progress with spinners
╭──────────────────────────────────────────╮
│ Transforming: Pride and Prejudice       │
├──────────────────────────────────────────┤
│ ⠋ Parsing book structure...             │
│ ✓ Identifying characters... (23 found)  │
│ ⠙ Analyzing gender markers...          │
│   Chapter 3 of 61 [█████░░░░░] 42%     │
│                                          │
│ Time: 00:01:23 | ETA: 00:02:11         │
╰──────────────────────────────────────────╯

# Multi-task progress
┌─ Book Processing ──────────────────────┐
│                                        │
│ pride.txt    ████████████ 100% ✓      │
│ alice.txt    ███████░░░░░  67% ↻      │
│ holmes.txt   ██░░░░░░░░░  23% ↻      │
│ gatsby.txt   ░░░░░░░░░░░   0% ⋯      │
│                                        │
│ Overall: 47% | 2.3 GB | 03:42 elapsed │
└────────────────────────────────────────┘
```

### Error Message Enhancement
```bash
/cli-ux errors --style helpful
```

Transforms error messages:
```bash
# Before
Error: Failed to parse file

# After
╭─ Error ────────────────────────────────────╮
│                                            │
│  ✗ Failed to parse file                   │
│                                            │
│  File: books/invalid.txt                  │
│  Issue: Unexpected format at line 42      │
│                                            │
│  The file appears to be HTML, not plain   │
│  text. Regender expects text or JSON.     │
│                                            │
│  💡 Suggestions:                           │
│  • Convert HTML to text first             │
│  • Use: pandoc invalid.txt -t plain       │
│  • Or download the text version           │
│                                            │
│  📚 Learn more:                            │
│  regender --help formats                  │
│                                            │
╰────────────────────────────────────────────╯
```

### Output Formatting
```bash
/cli-ux output --style rich
```

Creates beautiful output:
```bash
# Character Analysis Output
╭─ Character Analysis ───────────────────────╮
│                                            │
│  📖 Book: Pride and Prejudice              │
│  📊 Characters Found: 23                   │
│                                            │
├────────────────────────────────────────────┤
│  Primary Characters                        │
├────────────────────────────────────────────┤
│  • Elizabeth Bennet    │ Female │ Lead    │
│  • Fitzwilliam Darcy   │ Male   │ Lead    │
│  • Jane Bennet         │ Female │ Major   │
│  • Charles Bingley     │ Male   │ Major   │
├────────────────────────────────────────────┤
│  Secondary Characters (19 more)            │
│  Use --verbose to see all                 │
╰────────────────────────────────────────────╯

# Transformation Diff View
┌─ Transformation Preview ───────────────────┐
│                                            │
│  Original → Transformed                    │
│  ────────────────────────────────────      │
│                                            │
│  - She walked gracefully                  │
│  + He walked gracefully                   │
│                                            │
│  - her dress flowing                      │
│  + his coat flowing                       │
│                                            │
│  Context preserved ✓                      │
│  Grammar correct ✓                        │
│  Readability maintained ✓                 │
└────────────────────────────────────────────┘
```

### Help System Enhancement
```bash
/cli-ux help --examples
```

Creates comprehensive help:
```bash
$ regender --help

REGENDER-XYZ(1)                    User Commands

NAME
    regender - Transform gender representation in literature

SYNOPSIS
    regender [OPTIONS] <INPUT> <TRANSFORMATION> [OUTPUT]

DESCRIPTION
    AI-powered tool for analyzing and transforming gender
    representation in text using multiple LLM providers.

TRANSFORMATIONS
    gender_swap    Swap all gender representations
    all_female     Convert to female representation
    all_male       Convert to male representation
    non_binary     Use gender-neutral language

OPTIONS
    Input/Output:
      -i, --input FILE      Input text or JSON file
      -o, --output FILE     Output file (default: stdout)
      -f, --format FORMAT   Output format (json|text|diff)

    Processing:
      -p, --provider NAME   LLM provider (openai|anthropic|mlx)
      -m, --model NAME      Specific model to use
      --no-qc              Skip quality checks
      --cache              Enable caching

    Display:
      -v, --verbose        Detailed output
      -q, --quiet          Minimal output
      --no-color          Disable colors
      --progress          Show progress bar

    Interactive:
      -I, --interactive    Interactive mode
      --wizard            Guided setup wizard

EXAMPLES
    Transform a single book:
      $ regender pride.txt gender_swap -o output.json

    Batch process with progress:
      $ regender books/*.txt all_female --progress

    Interactive mode:
      $ regender --interactive

    Download and transform:
      $ regender --download 1342 | regender - gender_swap

    Compare transformations:
      $ regender book.txt gender_swap --format diff

CONFIGURATION
    Config file: ~/.regender/config.yaml
    Environment: REGENDER_PROVIDER, REGENDER_API_KEY

SEE ALSO
    regender-download(1), regender-batch(1)

BUGS
    Report issues at: github.com/user/regender-xyz

                                         v1.3.0
```

### Shell Completion
```bash
/cli-ux design completion
```

Generates shell completions:
```bash
# Bash completion
$ regender <TAB>
--help          --interactive   --verbose      pride.txt
--input         --output       --provider     alice.txt

$ regender pride.txt <TAB>
gender_swap    all_female    all_male    non_binary

$ regender --provider <TAB>
openai    anthropic    mlx    auto

# Zsh with descriptions
$ regender --<TAB>
--help        -- Show help message
--interactive -- Launch interactive mode
--verbose     -- Enable detailed output
--provider    -- Select LLM provider
```

### Aliases and Shortcuts
```bash
/cli-ux design shortcuts
```

Creates convenient aliases:
```bash
# Short flags for common operations
regender -I                    # --interactive
regender -P                    # --progress
regender -d 1342              # --download

# Subcommands for clarity
regender transform book.txt gender_swap
regender download 1342
regender batch books/*.txt
regender config set provider openai

# Smart defaults
regender book.txt            # Prompts for transformation
regender *.txt               # Auto-detects batch mode
```

## Style Guidelines

### Minimal Style
```bash
/cli-ux improve --style minimal
```
- No colors or decorations
- Simple text output
- Unix philosophy compliance
- Pipe-friendly

### Rich Style
```bash
/cli-ux improve --style rich
```
- Colors and emoji
- Box drawing characters
- Progress animations
- Interactive widgets

### Verbose Style
```bash
/cli-ux improve --style verbose
```
- Detailed logging
- Step-by-step output
- Debug information
- Timing metrics

## Testing CLI UX

```bash
/cli-ux test
```

Runs UX tests:
- Tab completion verification
- Help text clarity
- Error message usefulness
- Progress indicator accuracy
- Color contrast checking
- Response time measurement