# Examples

This directory contains example scripts demonstrating various features of the regender-xyz project.

## Character Analysis Examples

### analyze_large_book_rate_limited.py
Demonstrates how to analyze character data from large books that exceed API rate limits.

```bash
python examples/analyze_large_book_rate_limited.py
```

Features demonstrated:
- Rate-limited analysis for Grok API
- Automatic chunk management
- Progress tracking with token usage

## Running Examples

All examples assume you're in the project root directory and have set up your API keys:

```bash
export GROK_API_KEY='your-grok-api-key'
export OPENAI_API_KEY='your-openai-api-key'
```

## Rate Limiting

When using Grok-4-latest, the system automatically handles the 16k tokens/minute rate limit by:
1. Tracking token usage per chunk
2. Pausing when approaching the limit
3. Automatically resuming after the rate limit window resets

You can also manually enable rate limiting for other models:

```bash
python regender_book_cli.py analyze-characters books/json/mybook.json \
  -o books/json/mybook_characters.json \
  --rate-limited \
  --tokens-per-minute 10000
```