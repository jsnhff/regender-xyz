# Documentation

Welcome to regender-xyz! This tool transforms gender representation in books using AI.

## Quick Start

1. **Setup** - Copy `.env.example` to `.env` and add your API key(s)
2. **Transform a book** - Run: `python regender_book_cli.py regender yourbook.txt`

That's it! The system handles everything automatically.

## Documentation Guides

- **[Workflow Guide](WORKFLOW.md)** - How to use the system, transformation types, quality levels
- **[Architecture](ARCHITECTURE.md)** - System design, components, and data structures
- **[Providers Guide](PROVIDERS.md)** - Using OpenAI, Anthropic/Claude, or Grok

## Key Commands

```bash
# Transform with default settings (gender_swap, standard quality)
python regender_book_cli.py regender book.txt

# Transform to all female characters
python regender_book_cli.py regender book.txt --type all_female

# High quality mode (more thorough)
python regender_book_cli.py regender book.txt --quality high

# Use a specific provider
python regender_book_cli.py regender book.txt --provider anthropic

# List available books
python regender_book_cli.py list
```

## Tips for New Users

1. **Start with the unified workflow** - The `regender` command does everything
2. **Use flagship models** - Better accuracy means less proofreading
3. **Try standard quality first** - It's the best balance of speed and accuracy
4. **Save character analyses** - Reuse them for multiple transformations

Need help? Check the [Unified Workflow Guide](UNIFIED_WORKFLOW.md) for detailed examples.