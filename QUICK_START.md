# Quick Start Guide

## Installation

```bash
# Clone and setup
git clone https://github.com/yourusername/regender-xyz.git
cd regender-xyz
pip install -r requirements.txt

# Configure (choose one or both providers)
cp .env.example .env
# Edit .env with your API keys
```

## Basic Usage

### 1. Transform a Book (Simplest)

```bash
# Uses your default provider from .env
python regender_cli.py transform mybook.txt -t feminine
```

### 2. Process Project Gutenberg Books

```bash
# Download and process top 100 books
python gutenberg_cli.py pipeline

# Transform a specific book
python regender_json_cli.py gutenberg_json/pg1342-Pride_and_Prejudice_clean.json -t feminine
```

### 3. Use Different Providers

```bash
# Use Grok
python regender_cli.py transform book.txt -t feminine --provider grok

# Use OpenAI with specific model
python regender_cli.py transform book.txt -t feminine --provider openai --model gpt-4o-mini
```

## Model Recommendations

| Use Case | Recommended Model | Why |
|----------|-------------------|-----|
| Testing | gpt-4o-mini | Fast, cheap, good quality |
| Large books | grok-beta or gpt-4o | Fewer API calls (100 sent/chunk) |
| Quick processing | grok-3-mini-fast | Fast but more API calls |
| Best quality | gpt-4o | Best balance of all factors |

## Smart Chunking

The system automatically optimizes for each model:
- **Small context models** (gpt-4, grok-3-mini-fast): Smaller chunks
- **Large context models** (gpt-4o, grok-beta): Larger chunks
- **No configuration needed**: Just works!

## Checking Your Setup

```bash
# Test providers
python tests/test_providers.py

# See available providers
python -c "from api_client import UnifiedLLMClient; print(UnifiedLLMClient.list_available_providers())"
```

## Common Commands

```bash
# Preprocess book to JSON
python regender_cli.py preprocess book.txt

# Transform with verbose output
python regender_json_cli.py book.json -t feminine -v

# Full pipeline (analyze + transform)
python regender_cli.py pipeline book.txt -t feminine
```

## Tips

1. **Start small**: Test with a short text first
2. **Use verbose mode** (`-v`): See what's happening
3. **Check your credits**: Grok needs credits, OpenAI needs payment method
4. **Use .env file**: Easier than environment variables
5. **Let chunking work**: Don't override unless necessary

## Need Help?

- Check [Multi-Provider Guide](docs/reference/MULTI_PROVIDER_GUIDE.md)
- Read [Architecture Overview](docs/ARCHITECTURE.md)
- See [Complete Flow Diagram](docs/reference/COMPLETE_FLOW_DIAGRAM.md)