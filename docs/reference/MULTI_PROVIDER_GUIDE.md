# Multi-Provider LLM Support Guide

This guide explains how to use multiple LLM providers with regender-xyz.

## Overview

The system supports multiple LLM providers to give you flexibility in:
- **Cost optimization** - Choose the most cost-effective provider for your use case
- **Performance** - Select models based on speed vs quality needs
- **Redundancy** - Fallback to alternative providers if one is unavailable
- **Experimentation** - Compare results across different models

## Supported Providers

### OpenAI
- **Models**: GPT-4, GPT-4o, GPT-4o-mini, GPT-3.5-turbo
- **Strengths**: Mature API, excellent JSON mode, wide model selection
- **API Key**: `OPENAI_API_KEY`

### Grok (X.AI)
- **Models**: grok-beta
- **Strengths**: Competitive performance, alternative perspective
- **API Key**: `GROK_API_KEY`

## Configuration

### Method 1: Environment Variables

```bash
# OpenAI
export OPENAI_API_KEY='sk-...'

# Grok
export GROK_API_KEY='xai-...'
export GROK_API_BASE_URL='https://api.x.ai/v1'  # Optional, defaults to this

# Default provider (optional)
export LLM_PROVIDER='openai'  # or 'grok'
```

### Method 2: .env File

1. Copy the example:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env`:
   ```env
   OPENAI_API_KEY=sk-...
   GROK_API_KEY=xai-...
   LLM_PROVIDER=openai
   ```

3. Load with python-dotenv:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

### Method 3: Direct API Initialization

```python
from api_client import UnifiedLLMClient

# Use specific provider
client = UnifiedLLMClient(provider="grok")

# Auto-detect available provider
client = UnifiedLLMClient()
```

## Usage Examples

### Command Line

```bash
# Use default provider
python regender_cli.py transform book.txt -t feminine

# Use specific provider
python regender_cli.py transform book.txt -t feminine --provider grok

# Use specific model
python regender_cli.py transform book.txt -t feminine --provider openai --model gpt-4
```

### Python API

```python
from gender_transform_v2 import transform_text_file

# Use default provider
result = transform_text_file(
    "input.txt",
    "output.txt",
    "feminine"
)

# Use specific provider
result = transform_text_file(
    "input.txt",
    "output.txt",
    "feminine",
    provider="grok"
)

# Use specific model
result = transform_text_file(
    "input.txt",
    "output.txt",
    "feminine",
    provider="openai",
    model="gpt-4"
)
```

## Provider Selection Logic

The system selects a provider in this order:

1. **Explicit provider parameter** - If you specify `--provider` or `provider=`
2. **LLM_PROVIDER environment variable** - Your default preference
3. **Auto-detection** - First available provider (checks OpenAI, then Grok)

## Testing Your Configuration

Run the test script to verify your setup:

```bash
python test_providers.py
```

Expected output:
```
LLM Provider Configuration Test
==================================================

Environment Variables:
  OPENAI_API_KEY: Set
  GROK_API_KEY: Set
  LLM_PROVIDER: openai

Available providers: openai, grok

Testing auto-detection...
✓ Auto-detected provider: openai

Testing openai...
✓ openai client initialized
  Default model: gpt-4o-mini
✓ Test completion successful
  Response: Hello, World!
  Model used: gpt-4o-mini

Testing grok...
✓ grok client initialized
  Default model: grok-beta
✓ Test completion successful
  Response: Hello, World!
  Model used: grok-beta
```

## Handling Errors

### No API Keys Set
```
APIError: No LLM provider available. Set either OPENAI_API_KEY or GROK_API_KEY
```

**Solution**: Set at least one API key in your environment or .env file

### Invalid API Key
```
APIError: OpenAI API error: Invalid API key provided
```

**Solution**: Check that your API key is correct and active

### Provider Not Available
```
APIError: Provider grok is not properly configured
```

**Solution**: Ensure you have set the required environment variables for that provider

## Cost Considerations

Different providers and models have different costs:

- **OpenAI GPT-4**: High quality, higher cost
- **OpenAI GPT-4o-mini**: Good quality, lower cost
- **Grok**: Competitive pricing, check current rates

For large-scale processing, consider:
1. Using cheaper models for initial processing
2. Using expensive models only for complex cases
3. Implementing caching to avoid repeated API calls

## Advanced Usage

### Custom Provider Implementation

You can add support for additional providers by extending `BaseLLMClient`:

```python
from api_client import BaseLLMClient, APIResponse

class ClaudeClient(BaseLLMClient):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        # Initialize client...
    
    def complete(self, messages, model=None, temperature=0.0, response_format=None):
        # Implement completion logic
        pass
    
    def is_available(self):
        return bool(self.api_key)
    
    def get_default_model(self):
        return "claude-3-opus"
```

### Provider-Specific Features

Some features may only be available with certain providers:

- **JSON Mode**: Currently best supported by OpenAI
- **Streaming**: Implementation varies by provider
- **Function Calling**: Provider-specific implementations

The system handles these differences transparently where possible.

## Troubleshooting

### Check Available Providers
```python
from api_client import UnifiedLLMClient
providers = UnifiedLLMClient.list_available_providers()
print(f"Available: {providers}")
```

### Debug API Calls
```bash
# Enable debug logging
export REGENDER_DEBUG=1
```

### Disable Caching for Testing
```bash
export REGENDER_DISABLE_CACHE=1
```

## Security Notes

- **Never commit API keys** to version control
- Use `.env` files for local development
- Use environment variables in production
- Consider using key rotation for production systems
- Monitor API usage to detect anomalies

## Future Providers

The system is designed to easily add support for:
- Anthropic Claude
- Google Gemini
- Cohere
- Local models (via Ollama, etc.)

Contributions for additional providers are welcome!