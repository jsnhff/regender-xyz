# Multi-Provider LLM Support Guide v3

This guide explains how to use multiple LLM providers with regender-xyz. The system includes intelligent token-based chunking that adapts to each model's capabilities and smart character analysis for better transformation quality.

## Overview

The system supports multiple LLM providers to give you flexibility in:
- **Cost optimization** - Choose the most cost-effective provider for your use case
- **Performance** - Select models based on speed vs quality needs
- **Redundancy** - Fallback to alternative providers if one is unavailable
- **Smart chunking** - Automatic optimization based on model context windows
- **Character analysis** - Advanced LLM-based character identification

## Supported Providers

### OpenAI
- **Models**: 
  - GPT-4 (8k context) - Standard tier - Good for small texts
  - GPT-4o (128k context) - Flagship tier - Recommended for quality
  - GPT-4o-mini (128k context) - Advanced tier - Cost-effective
- **Strengths**: Mature API, excellent JSON mode, consistent quality
- **API Key**: `OPENAI_API_KEY`

### Grok (X.AI)
- **Models**: 
  - grok-3-latest (131k context) - Flagship tier - Best for character analysis
  - grok-3-mini-fast (32k context) - Standard tier - Fast processing
- **Strengths**: Largest context windows, excellent for comprehensive analysis
- **API Key**: `GROK_API_KEY`

### MLX (Local Models)
- **Models**: 
  - Mistral-7B-Instruct (32k context) - Standard tier - No API costs
  - Mistral-Small-24B (32k context) - Advanced tier - Requires ~45GB RAM
- **Strengths**: Privacy, no API costs, offline usage
- **Configuration**: `MLX_MODEL_PATH` environment variable

## Configuration

### Method 1: Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY='sk-...'

# Grok
export GROK_API_KEY='xai-...'
export GROK_API_BASE_URL='https://api.x.ai/v1'  # Optional

# Default provider (optional)
export LLM_PROVIDER='openai'  # or 'grok'
```

### Method 2: .env File (Recommended)

1. Copy the example:
   ```bash
   cp .env.example .env
   ```

2. Edit .env:
   ```env
   # OpenAI Configuration
   OPENAI_API_KEY=sk-...
   
   # Grok Configuration
   GROK_API_KEY=xai-...
   
   # Provider Selection
   LLM_PROVIDER=grok  # or openai or mlx
   
   # Model Overrides (optional)
   GROK_MODEL=grok-3-latest  # Recommended
   OPENAI_MODEL=gpt-4o
   
   # MLX Configuration (optional)
   MLX_MODEL_PATH=~/Models/mlx-community/Mistral-7B-Instruct-v0.3-4bit
   ```

The system automatically loads .env files, no additional setup required!

## Architecture

The multi-provider support is implemented through:

1. **`api_client.py`** - Unified interface with auto .env loading
2. **`book_transform/`** - Multi-provider transformation modules
3. **`book_characters/`** - LLM-based character analysis system
4. **`config/models.json`** - Model configurations and tier definitions
5. **Provider clients** - OpenAIClient, GrokClient, and MLXClient implementations

## Usage Examples

### Command Line with Book CLI

```bash
# Character analysis with Grok (recommended)
python regender_book_cli.py analyze-characters books/json/book.json \
  --provider grok \
  --model grok-3-latest \
  --output books/json/book_characters.json

# Transform using pre-analyzed characters
python regender_book_cli.py transform books/json/book.json \
  --characters books/json/book_characters.json \
  --type comprehensive \
  --provider grok \
  --output books/output/book_transformed.json

# Transform with automatic character analysis
python regender_book_cli.py transform books/json/book.json \
  --type comprehensive \
  --provider openai \
  --model gpt-4o

# Use local MLX model (no API costs)
python regender_book_cli.py transform books/json/book.json \
  --type comprehensive \
  --provider mlx
```

### Smart Chunking and Character Analysis

```bash
# Process a book from text to transformed output
# 1. Parse text to JSON
python regender_book_cli.py process --input books/texts --output books/json

# 2. Analyze characters (uses smart chunking for large books)
python regender_book_cli.py analyze-characters books/json/book.json \
  --provider grok --verbose

# 3. Transform with character context
python regender_book_cli.py transform books/json/book.json \
  --characters books/json/book_characters.json \
  --type comprehensive --verbose
```

### Python API

```python
from book_transform.utils import transform_with_characters
from book_characters import analyze_book_characters
from api_client import UnifiedLLMClient

# Analyze characters first
characters, context = analyze_book_characters(
    book_data,
    model="grok-3-latest",
    provider="grok"
)

# Transform with character context
transformed = transform_with_characters(
    book_data,
    characters=characters,
    transform_type="comprehensive",
    model="gpt-4o",
    provider="openai"
)

# Check available providers
providers = UnifiedLLMClient.list_available_providers()
print(f"Available: {providers}")
```

## Performance Comparison

### Character Analysis Performance (Harry Potter - 400k chars)

| Provider | Model | Time | Characters Found | Strategy |
|----------|-------|------|------------------|----------|
| Grok | grok-3-latest | 5-10 min | 106 | Smart chunking (5 strategic sections) |
| OpenAI | GPT-4o | 15-20 min | 85-95 | Standard chunking |
| MLX | Mistral-24B | 45+ min | 70-80 | Memory-aware chunking |

### Transformation Performance (with pre-analyzed characters)

| Provider | Model | Context | Speed | Quality | Cost |
|----------|-------|---------|-------|---------|------|
| OpenAI | GPT-4 | 8k | Slow | Good | High |
| OpenAI | GPT-4o | 128k | Fast | Excellent | Medium |
| OpenAI | GPT-4o-mini | 128k | Fastest | Good | Low |
| Grok | grok-3-latest | 131k | Fast | Excellent | Medium |
| Grok | grok-3-mini-fast | 32k | Fast | Good | Low |
| MLX | Mistral-7B | 32k | Medium | Good | Free |
| MLX | Mistral-24B | 32k | Slow | Very Good | Free |

## Smart Chunking System

The system automatically optimizes chunk sizes based on:

1. **Model context window** - Larger windows allow bigger chunks
2. **Token estimation** - Prevents context overflow
3. **Content analysis** - Adapts to sentence length
4. **Safety margins** - Ensures reliable processing

### Example: Chapter XVIII of Pride & Prejudice (137 sentences)

- **grok-3-mini-fast**: 5 chunks (30, 30, 30, 30, 17 sentences)
- **gpt-4o-mini**: 2 chunks (75, 62 sentences)
- **grok-3-latest**: 2 chunks (100, 37 sentences)

## Best Practices

### Model Selection
- **For character analysis**: Use grok-3-latest (best coverage with 131k context)
- **For transformation quality**: Use gpt-4o or grok-3-latest
- **For cost efficiency**: Use gpt-4o-mini with pre-analyzed characters
- **For privacy/offline**: Use MLX models on Apple Silicon
- **For large books**: Always pre-analyze characters, then transform

### Workflow Recommendations
1. **Parse** text to JSON first for better control
2. **Analyze** characters once with grok-3-latest
3. **Save** character analysis for reuse
4. **Transform** using any provider with character context
5. **Verify** output maintains paragraph structure

### Configuration Tips
1. Set `LLM_PROVIDER` in .env for consistency
2. Use `.env` files instead of exporting variables
3. Keep API keys secure - never commit them
4. Test with small texts first
5. Use `--verbose` to monitor progress

### Monitoring
- Use verbose mode (`--verbose`) to see processing details
- Check character count (100+ indicates good coverage)
- Monitor API costs through provider dashboards
- Save intermediate outputs for debugging

### Error Handling
```python
from api_client import APIError

try:
    result = transform_text_file("book.txt", "output.txt", "feminine")
except APIError as e:
    print(f"API Error: {e}")
    # Try fallback provider
```

## Troubleshooting

### No provider available
- Check API keys are set correctly
- Verify .env file is in project root
- Run `python tests/test_providers.py`

### API key conflicts
- Environment variables override .env file
- Use `unset GROK_API_KEY` if needed
- Check with `echo $GROK_API_KEY`

### Grok model selection
- Use `grok-3-latest` for best results
- Check `config/models.json` for available models
- Specify with `--model grok-3-latest`

### Character merging issues
- Family members being merged (e.g., Harry and Lily Potter)
- Solution: Use grok-3-latest with updated prompts
- The system now has explicit anti-merging rules

### Sentence splitting problems
- Abbreviations (Mr., Mrs., etc.) causing breaks
- Fixed in latest parser version
- Re-parse books if you see this issue

### Memory issues with MLX
- Mistral-24B needs ~45GB RAM
- Reduce chunk size in config if needed
- Monitor memory usage during processing

### Different results between providers
- This is normal - models have different styles
- Use character context for consistency
- Pre-analyze characters for best results

## Advanced Features

### Custom Chunk Sizes
```python
# Override automatic chunking
from json_transform import transform_chapter

# Force smaller chunks
result = transform_chapter(
    chapter, 
    "feminine", 
    character_context,
    sentences_per_chunk=20  # Override
)
```

### Token Monitoring
```python
from token_utils import analyze_book_for_chunking

# Analyze before processing
analysis = analyze_book_for_chunking(book_data, "gpt-4o-mini")
print(f"Estimated API calls: {analysis['estimated_api_calls']}")
print(f"Estimated tokens: {analysis['total_tokens']}")
```

### Provider Switching
```python
# Try primary, fallback to secondary
providers = ["openai", "grok"]
for provider in providers:
    try:
        result = transform_text_file(
            "input.txt", "output.txt", "feminine",
            provider=provider
        )
        break
    except APIError:
        continue
```

## Future Enhancements

- Additional providers (Claude, Gemini)
- Streaming support for real-time processing
- Parallel chunk processing
- Cost estimation before processing
- Provider-specific optimizations