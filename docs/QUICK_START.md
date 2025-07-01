# Quick Start Guide

## Installation

```bash
# Clone and setup
git clone https://github.com/yourusername/regender-xyz.git
cd regender-xyz
pip install -r requirements.txt

# Configure (choose one or more providers)
cp .env.example .env
# Edit .env with your API keys and/or MLX model path
```

## Basic Usage

### 1. Complete Book Pipeline (Recommended)

```bash
# Download, process, and transform books in one command
python regender_book_cli.py download --count 5
python regender_book_cli.py process
python regender_book_cli.py transform books/json/*.json --type comprehensive --batch

# Or use local MLX model (no API costs)
python regender_book_cli.py transform books/json/*.json --provider mlx --type comprehensive --batch
```

### 2. Transform Your Own Text Files

```bash
# Place your text files in the books/texts directory
cp ~/my_books/*.txt books/texts/

# Process to JSON format
python regender_book_cli.py process

# Transform with your preferred provider
python regender_book_cli.py transform books/json/mybook.json --type comprehensive --provider mlx
```

### 3. Working with Project Gutenberg

```bash
# Download specific number of top books
python regender_book_cli.py download --count 10

# List downloaded books
python regender_book_cli.py list

# Process all downloaded books to JSON
python regender_book_cli.py process

# Validate JSON files against source
python regender_book_cli.py validate

# Transform a specific book
python regender_book_cli.py transform books/json/Pride_and_Prejudice.json --type comprehensive
```

## Directory Structure

```
regender-xyz/
├── books/
│   ├── texts/        # Downloaded/source text files
│   ├── json/         # Processed JSON files
│   └── output/       # Transformed files (JSON and text)
```

## Using Different Providers

```bash
# Use local MLX model (no API costs, Apple Silicon only)
python regender_book_cli.py transform book.json --provider mlx

# Use Grok (requires API credits)
python regender_book_cli.py transform book.json --provider grok --model grok-beta

# Use OpenAI with specific model
python regender_book_cli.py transform book.json --provider openai --model gpt-4o-mini

# Use GPT-4o (best quality)
python regender_book_cli.py transform book.json --provider openai --model gpt-4o
```

## Model Recommendations

| Use Case | Recommended Provider/Model | Why |
|----------|----------------------------|-----|
| Testing | mlx (local) | Free, fast, private |
| API Testing | gpt-4o-mini | Fast, cheap, good quality |
| Large books | grok-beta or gpt-4o | Larger context windows |
| Quick processing | mlx or gpt-4o-mini | Fast and efficient |
| Best quality | gpt-4o | Best balance of all factors |
| Privacy-focused | mlx | All processing stays local |

## Smart Features

### Automatic Chunking
The system automatically optimizes chunk sizes for each model:
- Smaller chunks for models with limited context
- Larger chunks for models with big context windows
- No configuration needed!

### Character Analysis
- Automatically identifies characters and their genders
- Uses this context for more accurate transformations
- Falls back gracefully if analysis fails

### Validation
- Ensures JSON accurately represents source text
- Uses word-level similarity for robust comparison
- Generates detailed validation reports

## Common Workflows

### Full Book Processing
```bash
# Download and transform top 5 books to feminine
python regender_book_cli.py pipeline --count 5 --type feminine
```

### Process Existing Text Files
```bash
# Place your .txt files in books/texts/
cp ~/my_books/*.txt books/texts/

# Process and transform
python regender_book_cli.py process
python regender_book_cli.py transform books/json/*.json --type masculine --batch
```

### Single Book Transformation
```bash
# Transform with text output
python regender_book_cli.py transform books/json/mybook.json \
  --type comprehensive \
  --text books/output/mybook_transformed.txt
```

## Checking Your Setup

```bash
# Test providers
python tests/test_providers.py

# Run end-to-end test
python tests/e2e_test.py

# See available providers
python -c "from api_client import UnifiedLLMClient; print(UnifiedLLMClient.list_available_providers())"
```

## Transformation Types

- **comprehensive**: Transform all gender references (default)
- **names_only**: Only transform character names
- **pronouns_only**: Only transform pronouns

Note: The transformation direction is automatically determined based on character analysis.

## Tips

1. **Start small**: Test with 1-2 books first
2. **Check API credits**: Ensure you have credits/payment configured
3. **Use .env file**: Easier than environment variables
4. **Monitor costs**: Large books can use many API calls
5. **Let validation run**: Helps ensure quality

## Troubleshooting

### Import Errors
```bash
pip install -r requirements.txt
```

### API Errors
- Check your API keys in `.env`
- Verify you have credits (Grok) or payment method (OpenAI)
- Try a different model

### Memory Issues
- Process fewer books at once
- Use `--limit` flag for batch operations

## Need Help?

- Check the [Architecture Overview](ARCHITECTURE.md)
- See [Integration Summary](INTEGRATION_SUMMARY.md)
- Review [Multi-Provider Guide](reference/MULTI_PROVIDER_GUIDE.md)