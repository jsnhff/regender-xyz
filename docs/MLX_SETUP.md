# MLX Local Model Support

ReGender-XYZ supports running local models using MLX on Apple Silicon Macs. This allows you to transform books and analyze characters without API costs using models like Mistral-7B-Instruct or Mistral-Small-24B.

## Prerequisites

1. **Apple Silicon Mac** (M1, M2, M3, etc.)
2. **mlx-lm installed**: `pip install mlx-lm`
3. **A compatible MLX model** downloaded locally

## Setup

### 1. Install mlx-lm

```bash
pip install mlx-lm
```

### 2. Download a Model (if needed)

If you don't already have a model, you can download one:

```bash
# Download Mistral-7B-Instruct 8-bit quantized
python -m mlx_lm.convert \
    --hf-path mistralai/Mistral-7B-Instruct-v0.3 \
    -q \
    --q-bits 8 \
    --mlx-path ~/Models/mlx-community/Mistral-7B-Instruct-v0.3-8bit
```

### 3. Configure .env

Add the path to your MLX model in your `.env` file:

```bash
# Local Model Configuration (MLX)
MLX_MODEL_PATH=/Users/williambarnes/Models/mlx-community/Mistral-7B-Instruct-v0.3-8bit

# Optionally set MLX as default provider
DEFAULT_LLM_PROVIDER=mlx
```

## Usage

### Using MLX with the CLI

```bash
# Analyze characters in a book
python regender_book_cli.py analyze-characters book.json --provider mlx

# Transform a single book
python regender_book_cli.py transform book.json --provider mlx

# Transform with pre-analyzed characters
python regender_book_cli.py transform book.json \
  --characters book_characters.json \
  --provider mlx

# Use Mistral-24B for better quality (requires ~45GB RAM)
python regender_book_cli.py transform book.json \
  --provider mlx \
  --model mistral-small-24b
```

### Testing MLX Support

Run the test script to verify MLX is working:

```bash
python test_mlx.py
```

## Performance Notes

### Model Comparison

| Model | Memory Usage | Speed | Context | Quality | Use Case |
|-------|--------------|-------|---------|---------|----------|
| Mistral-7B-8bit | ~7-8GB | Fast | 32K | Good | Quick transforms |
| Mistral-Small-24B | ~45GB | Slow | 32K | Very Good | Character analysis |

### Character Analysis Performance
- **Mistral-7B**: 15-20 minutes for full book, finds 60-80 characters
- **Mistral-24B**: 45+ minutes for full book, finds 70-80 characters
- **Recommendation**: Use Grok API for character analysis if available

### Memory-Aware Chunking
The system automatically adjusts chunk sizes for MLX models:
- Default: 150k characters per chunk
- Memory-constrained (24B on 64GB system): 50k characters per chunk
- Overlap: 2000 characters between chunks

## Supported Models

Tested and optimized for:
- **Mistral-7B-Instruct-v0.3** (8-bit recommended) - Fast, efficient
- **Mistral-Small-24B** (16-bit) - Better quality, high memory usage
- Other MLX models may work but require configuration adjustments

## Troubleshooting

### "mlx-lm not installed"
```bash
pip install mlx-lm
```

### "Model path does not exist"
- Check your MLX_MODEL_PATH in .env
- Ensure the path points to the model directory containing config.json

### "Failed to load MLX model"
- Verify the model is in MLX format (not HuggingFace format)
- Try re-downloading or converting the model

### Poor quality output
- Local models may need different prompting strategies
- Try adjusting temperature: `--temperature 0.3`
- Consider using a larger model or API provider for critical work