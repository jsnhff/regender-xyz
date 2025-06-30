# Multi-Provider LLM Support Guide v2

This guide explains how to use multiple LLM providers with regender-xyz. The system includes intelligent token-based chunking that adapts to each model's capabilities.

## Overview

The system supports multiple LLM providers to give you flexibility in:
- **Cost optimization** - Choose the most cost-effective provider for your use case
- **Performance** - Select models based on speed vs quality needs
- **Redundancy** - Fallback to alternative providers if one is unavailable
- **Smart chunking** - Automatic optimization based on model context windows

## Supported Providers

### OpenAI
- **Models**: 
  - GPT-4 (8k context) - 50 sentences/chunk
  - GPT-4o (128k context) - 100 sentences/chunk - Recommended
  - GPT-4o-mini (128k context) - 75 sentences/chunk - Cost-effective
- **Strengths**: Mature API, excellent JSON mode, wide model selection
- **API Key**: `OPENAI_API_KEY`

### Grok (X.AI)
- **Models**: 
  - grok-beta (131k context) - 100 sentences/chunk - High capacity
  - grok-3-mini-fast (32k context) - 30 sentences/chunk - Fast processing
- **Strengths**: Large context windows, competitive performance
- **API Key**: `GROK_API_KEY`

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
   LLM_PROVIDER=grok  # or openai
   
   # Model Overrides (optional)
   GROK_MODEL=grok-3-mini-fast
   ```

The system automatically loads .env files, no additional setup required!

## Architecture

The multi-provider support is implemented through:

1. **`api_client.py`** - Unified interface with auto .env loading
2. **`gender_transform.py`** - Multi-provider transformation module
3. **`token_utils.py`** - Intelligent chunking algorithms
4. **`model_configs.py`** - Model-specific configurations
5. **Provider clients** - OpenAIClient and GrokClient implementations

## Usage Examples

### Command Line

```bash
# Use default provider (from environment)
python regender_cli.py transform book.txt -t feminine

# Explicitly use Grok
python regender_cli.py transform book.txt -t feminine --provider grok

# Use specific model
python regender_cli.py transform book.txt -t feminine --provider openai --model gpt-4o-mini
```

### JSON Processing with Smart Chunking

```bash
# Automatic provider detection and model-optimized chunking
python regender_json_cli.py book.json -t feminine -o output.json -v

# With verbose mode, you'll see:
# - Provider being used
# - Model selected
# - Chunk sizes per chapter
# - Token estimates
```

### Python API

```python
from gender_transform import transform_text_file
from api_client import UnifiedLLMClient

# Use default provider
result = transform_text_file(
    "input.txt",
    "output.txt",
    "feminine"
)

# Explicitly use Grok with specific model
result = transform_text_file(
    "input.txt",
    "output.txt",
    "feminine",
    provider="grok",
    model="grok-3-mini-fast"
)

# Check available providers
providers = UnifiedLLMClient.list_available_providers()
print(f"Available: {providers}")
```

## Performance Comparison

| Provider | Model | Context | Chunks/4K sent | Speed | Cost | API Calls* |
|----------|-------|---------|----------------|-------|------|------------|
| OpenAI | GPT-4 | 8k | 50 sent | Slow | High | ~111 |
| OpenAI | GPT-4o | 128k | 100 sent | Fast | Medium | ~69 |
| OpenAI | GPT-4o-mini | 128k | 75 sent | Fastest | Low | ~79 |
| Grok | grok-beta | 131k | 100 sent | Fast | Medium | ~69 |
| Grok | grok-3-mini-fast | 32k | 30 sent | Fast | Low | ~158 |

*API calls for Pride & Prejudice (4,029 sentences)

## Smart Chunking System

The system automatically optimizes chunk sizes based on:

1. **Model context window** - Larger windows allow bigger chunks
2. **Token estimation** - Prevents context overflow
3. **Content analysis** - Adapts to sentence length
4. **Safety margins** - Ensures reliable processing

### Example: Chapter XVIII of Pride & Prejudice (137 sentences)

- **grok-3-mini-fast**: 5 chunks (30, 30, 30, 30, 17 sentences)
- **gpt-4o-mini**: 2 chunks (75, 62 sentences)
- **grok-beta**: 2 chunks (100, 37 sentences)

## Best Practices

### Model Selection
- **For large books**: Use gpt-4o or grok-beta (fewer API calls)
- **For quick tests**: Use gpt-4o-mini or grok-3-mini-fast
- **For quality**: Use gpt-4o (best balance)
- **For cost**: Use gpt-4o-mini (most economical)

### Configuration Tips
1. Set `LLM_PROVIDER` in .env for consistency
2. Use `.env` files instead of exporting variables
3. Keep API keys secure - never commit them
4. Test with small texts first

### Monitoring
- Use verbose mode (`-v`) to see chunk processing
- Check logs for token usage estimates
- Monitor API costs through provider dashboards

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

### Context length exceeded
- The smart chunking should prevent this
- If it occurs, check for unusually long sentences
- File an issue with details

### Grok credits error
- New Grok accounts need credits
- Purchase at https://console.x.ai/
- Check usage at the same URL

### Different results between providers
- This is normal - models have different styles
- Test both to find your preference
- Character context helps consistency

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