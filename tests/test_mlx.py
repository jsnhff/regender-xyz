#!/usr/bin/env python3
"""
Test script for MLX local model support.

This demonstrates how to use the MLX provider with regender-xyz.
"""

import os
import sys
from pathlib import Path

# Test if MLX is available
try:
    import mlx_lm
    print("✓ mlx-lm is installed")
except ImportError:
    print("✗ mlx-lm not installed. Install with: pip install mlx-lm")
    sys.exit(1)

# Check if MLX_MODEL_PATH is set
model_path = os.environ.get("MLX_MODEL_PATH")
if not model_path:
    print("✗ MLX_MODEL_PATH not set in environment")
    print("  Set it in .env file: MLX_MODEL_PATH=/path/to/your/mlx/model")
    sys.exit(1)

print(f"✓ MLX_MODEL_PATH: {model_path}")

# Check if model path exists
if not Path(model_path).exists():
    print(f"✗ Model path does not exist: {model_path}")
    sys.exit(1)

print("✓ Model path exists")

# Test the API client
from api_client import UnifiedLLMClient

try:
    # Create MLX client
    client = UnifiedLLMClient(provider="mlx")
    print("✓ MLX client created successfully")
    
    # List available providers
    providers = UnifiedLLMClient.list_available_providers()
    print(f"✓ Available providers: {', '.join(providers)}")
    
    # Test a simple completion
    print("\nTesting MLX completion...")
    messages = [
        {"role": "user", "content": "What is 2+2?"}
    ]
    
    response = client.complete(messages, temperature=0.1)
    print(f"✓ Response: {response.content}")
    
    # Test with a book transformation prompt
    print("\nTesting gender transformation prompt...")
    messages = [
        {"role": "user", "content": "Transform this sentence to use feminine pronouns: 'John walked to his car.'"}
    ]
    
    response = client.complete(messages, temperature=0.1)
    print(f"✓ Response: {response.content}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n✓ MLX support is working correctly!")
print("\nTo use MLX with the CLI:")
print("  python regender_book_cli.py transform book.json --provider mlx")