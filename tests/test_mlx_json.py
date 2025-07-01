#!/usr/bin/env python3
"""Test script to verify MLX JSON handling fixes."""

import os
import json

# Set MLX as the provider
os.environ['LLM_PROVIDER'] = 'mlx'

# Import after setting environment
from book_transform.character_analyzer import analyze_characters
from api_client import UnifiedLLMClient

def test_mlx_json_response():
    """Test MLX model's ability to generate JSON responses."""
    print("Testing MLX JSON response handling...")
    
    # Simple test text
    test_text = """Alice went to the store. She bought some apples.
    Bob was waiting at home. He was preparing dinner."""
    
    try:
        # Test character analysis
        print("\n1. Testing character analysis with MLX...")
        result = analyze_characters(test_text, provider='mlx')
        print(f"Success! Found {len(result.get('characters', {}))} characters")
        print(f"Characters: {list(result.get('characters', {}).keys())}")
        
    except Exception as e:
        print(f"Character analysis failed: {e}")
        print("\nTesting raw MLX JSON generation...")
        
        # Test raw MLX response
        client = UnifiedLLMClient(provider='mlx')
        response = client.complete(
            messages=[
                {"role": "user", "content": "Generate a simple JSON object with name and age fields. Respond ONLY with valid JSON."}
            ],
            temperature=0
        )
        
        print(f"Raw response: {response.content}")
        
        # Try to parse it
        try:
            parsed = json.loads(response.content)
            print(f"Successfully parsed: {parsed}")
        except json.JSONDecodeError as je:
            print(f"Failed to parse: {je}")
            
            # Show what our JSON extraction would do
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response.content, re.DOTALL)
            if json_match:
                print(f"Extracted JSON: {json_match.group(0)}")
                try:
                    parsed = json.loads(json_match.group(0))
                    print(f"Successfully parsed extracted JSON: {parsed}")
                except:
                    print("Failed to parse extracted JSON")

if __name__ == "__main__":
    test_mlx_json_response()