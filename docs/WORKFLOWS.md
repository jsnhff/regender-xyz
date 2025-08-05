# Regender-XYZ Workflows

## Overview

This document details all workflows available in the Regender-XYZ system, including standard pipelines, quality control processes, and advanced features.

## 1. Basic Book Processing Workflow

### Download → Parse → Transform → Output

```bash
# Step 1: Download a book
python regender_book_cli.py download 1342  # Pride and Prejudice

# Step 2: Parse to JSON
python regender_book_cli.py process books/texts/pg1342-Pride_and_Prejudice.txt

# Step 3: Transform gender
python regender_book_cli.py transform books/json/pg1342-Pride_and_Prejudice.json --type all_male

# Result: books/output/pg1342-Pride_and_Prejudice_all_male.txt
```

## 2. Character-Aware Transformation Workflow

### Analyze Characters → Transform with Context

```bash
# Step 1: Analyze characters in the book
python regender_book_cli.py analyze-characters books/json/pg1342-Pride_and_Prejudice.json \
    -o books/json/pg1342-Pride_and_Prejudice_characters.json

# Step 2: Transform using character context
python regender_book_cli.py transform books/json/pg1342-Pride_and_Prejudice.json \
    --type gender_swap \
    --character-file books/json/pg1342-Pride_and_Prejudice_characters.json

# Result: More accurate transformation aware of character genders
```

## 3. Quality Control Workflow

### Transform → Review → Correct

```bash
# Step 1: Standard transformation
python regender_book_cli.py transform books/json/pg1342-Pride_and_Prejudice.json --type all_female

# Step 2: Run quality control
python run_review_loop.py books/output/pg1342-Pride_and_Prejudice_all_female.txt all_female

# Result: books/output/pg1342-Pride_and_Prejudice_all_female_qc.txt
```

The quality control loop:
1. Scans for gendered language patterns
2. Uses AI to identify missed transformations
3. Applies corrections iteratively
4. Saves quality-controlled version

## 4. Rate-Limited Analysis Workflow

### For Large Books with API Limits

```bash
# For books that exceed API rate limits (e.g., Dracula)
python regender_book_cli.py analyze-characters books/json/pg345-Dracula.json \
    --provider grok \
    --model grok-4-latest \
    --rate-limited \
    --tokens-per-minute 16000

# Or use the example script
python examples/analyze_large_book_rate_limited.py
```

Features:
- Tracks token usage per minute
- Automatically pauses when approaching limits
- Shows progress with time estimates
- Preserves partial results

## 5. Batch Processing Workflow

### Process Multiple Books

```bash
# Download top 100 books
python regender_book_cli.py download --count 100

# Process all to JSON
python regender_book_cli.py process books/texts/

# List available books
python regender_book_cli.py list

# Transform specific books
for book in books/json/*.json; do
    python regender_book_cli.py transform "$book" --type all_male
done
```

## 6. Multi-Provider Workflow

### Switch Between AI Providers

```bash
# Use OpenAI (default)
export LLM_PROVIDER=openai
python regender_book_cli.py transform books/json/pg1342.json --type all_female

# Switch to Grok for larger context
export LLM_PROVIDER=grok
python regender_book_cli.py transform books/json/pg345-Dracula.json --type gender_swap

```

## 7. Validation Workflow

### Ensure Data Integrity

```bash
# Validate JSON structure
python regender_book_cli.py validate books/json/pg1342-Pride_and_Prejudice.json

# Check character data
python regender_book_cli.py validate books/json/pg1342_characters.json --type characters

# Validate transformation output
python regender_book_cli.py validate books/output/pg1342_all_male.txt --check-transformation all_male
```

## 8. Advanced Transformation Workflow

### Custom Parameters and Fine Control

```bash
# Transform with specific model
python regender_book_cli.py transform books/json/pg1342.json \
    --type gender_swap \
    --model gpt-4o \
    --provider openai

# Transform with verbose output
python regender_book_cli.py transform books/json/pg1342.json \
    --type all_male \
    --verbose

# Transform with custom output path
python regender_book_cli.py transform books/json/pg1342.json \
    --type all_female \
    --output custom_output/my_transformed_book.txt
```

## 9. Development and Testing Workflow

### For Contributors and Developers

```bash
# Run provider tests
python tests/test_providers.py

# Test character analysis
python tests/test_characters.py

# End-to-end testing
python tests/test_end_to_end.py

# Test with specific provider
LLM_PROVIDER=grok python tests/test_comprehensive.py
```

## 10. Debugging Workflow

### Troubleshooting Issues

```bash
# Enable debug logging
export DEBUG=1
python regender_book_cli.py transform books/json/pg1342.json --type all_male

# Check logs
tail -f logs/transform_*.log

# Test API connection
python -c "from api_client import UnifiedLLMClient; client = UnifiedLLMClient(); print(client.test_connection())"

# Validate model configuration
python -c "import json; print(json.dumps(json.load(open('config/models.json'))['models']['grok-4-latest'], indent=2))"
```

## Common Workflow Patterns

### Pattern 1: Quick Test
```bash
# Download, process, and transform a small book
python regender_book_cli.py download 11  # Alice in Wonderland
python regender_book_cli.py process books/texts/pg11-*.txt
python regender_book_cli.py transform books/json/pg11-*.json --type all_female
```

### Pattern 2: Production Pipeline
```bash
# Full pipeline with quality control
book="pg1342-Pride_and_Prejudice"
python regender_book_cli.py process books/texts/${book}.txt
python regender_book_cli.py analyze-characters books/json/${book}.json
python regender_book_cli.py transform books/json/${book}.json \
    --type gender_swap \
    --character-file books/json/${book}_characters.json
python run_review_loop.py books/output/${book}_gender_swap.txt gender_swap
```

### Pattern 3: Bulk Analysis
```bash
# Analyze characters for all books
for json_file in books/json/pg*.json; do
    if [[ ! -f "${json_file%.json}_characters.json" ]]; then
        echo "Analyzing $json_file..."
        python regender_book_cli.py analyze-characters "$json_file" \
            --rate-limited --tokens-per-minute 16000
    fi
done
```

## Tips and Best Practices

1. **Start Small**: Test with shorter books first (Alice in Wonderland, Jekyll & Hyde)
2. **Use Character Analysis**: Always analyze characters for better transformation quality
3. **Monitor Rate Limits**: Use `--rate-limited` flag for large books with Grok
4. **Quality Control**: Run review loop for production-quality output
5. **Save Intermediate Files**: Keep JSON and character files for reproducibility
6. **Check Logs**: Review logs in `logs/` directory for debugging
7. **Validate Output**: Use validation commands to ensure data integrity