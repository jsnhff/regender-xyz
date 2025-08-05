#!/usr/bin/env python3
"""
Example: Analyzing a large book with rate limiting

This example shows how to analyze character data from large books
like Dracula that exceed API rate limits.
"""

import subprocess
import sys

def main():
    # Example book file
    book_file = "books/json/pg345-Dracula_clean.json"
    output_file = "books/json/pg345-Dracula_characters_rate_limited.json"
    
    print("📚 Example: Analyzing Dracula with rate limiting")
    print("=" * 50)
    print(f"Input:  {book_file}")
    print(f"Output: {output_file}")
    print()
    
    # Run the analyze-characters command with rate limiting
    cmd = [
        sys.executable, "regender_book_cli.py",
        "analyze-characters",
        book_file,
        "-o", output_file,
        "--provider", "grok",
        "--model", "grok-4-latest",
        "--rate-limited",
        "--tokens-per-minute", "16000"
    ]
    
    print("Running command:")
    print(" ".join(cmd))
    print()
    
    # Execute the command
    subprocess.run(cmd)

if __name__ == "__main__":
    main()