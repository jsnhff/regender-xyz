#!/usr/bin/env python3
"""
Test script to verify LLM provider configuration.
"""

import os
import sys
from api_client import UnifiedLLMClient, APIError


def test_provider(provider_name: str):
    """Test a specific provider."""
    print(f"\nTesting {provider_name}...")
    
    try:
        client = UnifiedLLMClient(provider=provider_name)
        print(f"✓ {provider_name} client initialized")
        print(f"  Default model: {client.get_default_model()}")
        
        # Try a simple completion
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, World!' and nothing else."}
        ]
        
        response = client.complete(messages)
        print(f"✓ Test completion successful")
        print(f"  Response: {response.content.strip()}")
        print(f"  Model used: {response.model}")
        
        return True
        
    except APIError as e:
        print(f"✗ {provider_name} test failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error testing {provider_name}: {e}")
        return False


def main():
    """Test all configured providers."""
    print("LLM Provider Configuration Test")
    print("=" * 50)
    
    # Check environment variables
    print("\nEnvironment Variables:")
    print(f"  OPENAI_API_KEY: {'Set' if os.environ.get('OPENAI_API_KEY') else 'Not set'}")
    print(f"  GROK_API_KEY: {'Set' if os.environ.get('GROK_API_KEY') else 'Not set'}")
    print(f"  LLM_PROVIDER: {os.environ.get('LLM_PROVIDER', 'Not set (auto-detect)')}")
    
    # List available providers
    try:
        available = UnifiedLLMClient.list_available_providers()
        print(f"\nAvailable providers: {', '.join(available) if available else 'None'}")
    except Exception as e:
        print(f"\nError checking available providers: {e}")
        available = []
    
    # Test auto-detection
    print("\nTesting auto-detection...")
    try:
        client = UnifiedLLMClient()
        print(f"✓ Auto-detected provider: {client.get_provider()}")
    except APIError as e:
        print(f"✗ Auto-detection failed: {e}")
    
    # Test each provider if available
    if 'openai' in available:
        test_provider('openai')
    
    if 'grok' in available:
        test_provider('grok')
    
    if not available:
        print("\n⚠ No providers are configured!")
        print("\nTo configure providers:")
        print("  1. Copy .env.example to .env")
        print("  2. Add your API keys")
        print("  3. Run this test again")


if __name__ == "__main__":
    main()