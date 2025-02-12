#!/usr/bin/env python3
"""
Text Transformer - A tool for transforming gender representation in literature
Version: 0.1.0
"""

import os
import sys
from typing import Optional, Tuple
from character_analysis import find_characters

def load_text(file_path: str) -> Tuple[Optional[str], str]:
    """Load input text file with validation.
    
    Args:
        file_path (str): Path to the input text file
        
    Returns:
        tuple: (content, status_message)
            - content: The text content if successful, None if failed
            - status_message: A user-friendly status message
    """
    try:
        if not os.path.exists(file_path):
            return None, f"Error: File '{file_path}' not found"
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        if not content.strip():
            return None, f"Error: File '{file_path}' is empty"
            
        return content, "File loaded successfully"
    except Exception as e:
        return None, f"Error reading file: {str(e)}"

def print_character_info(name: str, character) -> None:
    """Print detailed information about a character."""
    print(f"\nCharacter: {name}")
    print("-" * 60)
    print(f"Role: {character.role or 'Unknown'}")
    print(f"Gender: {character.gender or 'Unknown'}")
    print(f"Mentions: {len(character.mentions)} times")
    if character.name_variants:
        print("Name variations found:")
        for variant in character.name_variants:
            if variant != name:  # Don't show canonical name in variants
                print(f"  - {variant}")
    print("-" * 60)

def main():
    """Main application entry point."""
    if len(sys.argv) != 2:
        print("Usage: python main.py <input_file>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    content, message = load_text(input_file)
    
    if content is None:
        print(message)
        sys.exit(1)
        
    print(message)
    
    # Find characters in the text
    characters = find_characters(content)
    
    # Print found characters and their information
    print(f"\nFound {len(characters)} characters:")
    for name, character in characters.items():
        print_character_info(name, character)

if __name__ == "__main__":
    main()
