# MLX Local Model Support

ReGender-XYZ now supports running local models using MLX on Apple Silicon Macs. This allows you to transform books without API costs using models like Mistral-7B-Instruct.

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
# Transform a single book
python regender_book_cli.py transform book.json --provider mlx

# Transform with specific model (if you have multiple)
python regender_book_cli.py transform book.json --provider mlx --model mistral-7b-instruct

# Batch transform
python regender_book_cli.py transform book_json/ --batch --provider mlx
```

### Testing MLX Support

Run the test script to verify MLX is working:

```bash
python test_mlx.py
```

## Performance Notes

- **Memory Usage**: Mistral-7B 8-bit requires ~7-8GB of RAM
- **Speed**: Expect 10-50 tokens/second depending on your Mac
- **Context Window**: Mistral-7B supports 32K tokens (much larger than GPT-3.5)
- **Quality**: Local models may produce different results than GPT-4

## Supported Models

Currently optimized for:
- Mistral-7B-Instruct (all versions)
- Mistral-7B-Instruct-v0.3-8bit (recommended)

Other MLX models may work but haven't been tested.

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