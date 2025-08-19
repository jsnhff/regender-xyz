# Multi-Provider LLM Support Guide

This guide explains how to use different AI providers with regender-xyz.

## Supported Providers

### OpenAI
- **Models**: GPT-4o (recommended), GPT-4o-mini, GPT-4 Turbo
- **Best for**: Reliable quality, good JSON support
- **Context**: 128k tokens
- **Setup**: Add `OPENAI_API_KEY` to your .env file

### Anthropic (Claude)
- **Models**: Claude Opus 4 (recommended), Claude 3.5 Sonnet, Claude 3 Opus
- **Best for**: Highest quality output, nuanced understanding
- **Context**: 200k tokens
- **Setup**: Add `ANTHROPIC_API_KEY` to your .env file

### Grok (X.AI)
- **Models**: Grok-4-latest (recommended), Grok-3-latest, Grok-beta
- **Best for**: Large context windows, comprehensive analysis
- **Context**: 256k tokens (Grok-4), 131k tokens (Grok-3)
- **Setup**: Add `GROK_API_KEY` to your .env file
- **Note**: Grok-4 has 16k tokens/minute rate limit

## Quick Setup

1. Copy `.env.example` to `.env`
2. Add your API keys:
   ```
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   GROK_API_KEY=xai-...
   ```
3. Set your default provider (optional):
   ```
   DEFAULT_PROVIDER=anthropic
   ```

## Using Different Providers

### Default Provider
```bash
# Uses DEFAULT_PROVIDER from .env, or auto-detects
python regender_book_cli.py regender book.txt
```

### Specify Provider
```bash
# Use OpenAI
python regender_book_cli.py regender book.txt --provider openai

# Use Anthropic/Claude
python regender_book_cli.py regender book.txt --provider anthropic

# Use Grok
python regender_book_cli.py regender book.txt --provider grok
```

### Specify Model
```bash
# Use specific OpenAI model
python regender_book_cli.py regender book.txt --provider openai --model gpt-4o-mini

# Use specific Claude model
python regender_book_cli.py regender book.txt --provider anthropic --model claude-3-5-sonnet-latest

# Use Grok-3 instead of Grok-4
python regender_book_cli.py regender book.txt --provider grok --model grok-3-latest
```

## Provider Comparison

| Provider | Best Model | Context | Speed | Quality | Cost |
|----------|------------|---------|-------|---------|------|
| OpenAI | GPT-4o | 128k | Fast | Excellent | $$ |
| Anthropic | Claude Opus 4 | 200k | Medium | Best | $$$ |
| Grok | Grok-4-latest | 256k | Medium | Excellent | $$ |

## Recommendations

1. **For highest quality**: Use Anthropic with Claude Opus 4
2. **For best value**: Use OpenAI with GPT-4o
3. **For large books**: Use Grok-4-latest (best context window)
4. **For rate-limited APIs**: The system handles this automatically

## Rate Limiting

Some providers have rate limits:
- **Grok-4**: 16k tokens/minute (handled automatically)
- **Others**: Generally more generous limits

The system automatically manages rate limits by:
- Tracking token usage
- Pausing when approaching limits
- Resuming after rate window resets

## Troubleshooting

### Check Available Providers
```bash
# This will show which providers are configured
python regender_book_cli.py list
```

### Provider Not Found
- Ensure API key is set in .env
- Check key format (OpenAI: sk-..., Anthropic: sk-ant-..., Grok: xai-...)
- Try specifying provider explicitly with --provider flag

### Rate Limit Errors
- For Grok-4, rate limiting is automatic
- For other providers, wait and retry
- Consider using a different model temporarily