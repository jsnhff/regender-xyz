#!/usr/bin/env python3
"""Simple test of MLX functionality."""

import json
from api_client import UnifiedLLMClient

# Create a simple test book
test_book = {
    "metadata": {
        "title": "Test Book",
        "author": "Test Author"
    },
    "chapters": [
        {
            "number": 1,
            "title": "Chapter 1",
            "sentences": [
                "John walked to his car.",
                "He opened the door and got in.",
                "His keys were in his pocket."
            ]
        }
    ]
}

# Save test book
with open("test_book.json", "w") as f:
    json.dump(test_book, f, indent=2)

print("Testing MLX transformation...")

# Test direct API call first
try:
    client = UnifiedLLMClient(provider="mlx")
    messages = [
        {"role": "user", "content": "Transform this sentence to use feminine pronouns: 'John walked to his car.'"}
    ]
    
    response = client.complete(messages, temperature=0.1)
    print(f"✓ Direct API test passed: {response.content[:100]}...")
    
except Exception as e:
    print(f"✗ Direct API test failed: {e}")
    import traceback
    traceback.print_exc()

# Now test with the CLI
print("\nTesting with CLI...")
import subprocess
import sys

result = subprocess.run([
    sys.executable, "regender_book_cli.py", "transform", 
    "test_book.json", 
    "--provider", "mlx",
    "--type", "comprehensive",
    "-o", "test_book_transformed.json"
], capture_output=True, text=True)

if result.returncode == 0:
    print("✓ CLI test passed")
    # Check the output
    with open("test_book_transformed.json", "r") as f:
        transformed = json.load(f)
        if transformed.get("transformation", {}).get("total_changes", 0) > 0:
            print(f"✓ Made {transformed['transformation']['total_changes']} changes")
        else:
            print("⚠ No changes made")
else:
    print(f"✗ CLI test failed: {result.stderr}")