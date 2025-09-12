#!/usr/bin/env python3
"""
Quick script to run character analysis with proper environment setup.
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the CLI
from regender_cli import main

if __name__ == '__main__':
    # Ensure environment is set
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY not found in environment or .env file")
        sys.exit(1)
    
    print(f"Using OpenAI API key: {os.getenv('OPENAI_API_KEY')[:20]}...")
    
    # Run the CLI
    main()