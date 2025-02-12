#!/usr/bin/env python3
"""
Text Transformer - A tool for transforming gender representation in literature
Version: 0.1.0
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple
from character_analysis import (
    find_characters, Mention, 
    save_character_analysis, load_character_analysis
)

def load_text(file_path: str) -> Tuple[Optional[str], str]:
    """Load and validate input text file."""
    try:
        if not os.path.exists(file_path):
            return None, f"Error: File '{file_path}' not found"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        if not content:
            return None, f"Error: File '{file_path}' is empty"
            
        return content, "File loaded successfully"
    except Exception as e:
        return None, f"Error reading file: {str(e)}"

def print_mention_group(mentions: list[Mention], group_type: str) -> None:
    """Print a group of mentions with sample contexts."""
    if not mentions:
        return
        
    print(f"\n{group_type.title()} mentions ({len(mentions)}):")
    # Show up to 3 examples
    for mention in mentions[:3]:
        print(f"  {mention.text:>10}: ...{mention.context}...")
    if len(mentions) > 3:
        print(f"  ... and {len(mentions) - 3} more {group_type} mentions ...")

def print_character_info(name: str, character) -> None:
    """Print character information in a clean, organized format."""
    print(f"\nCharacter: {name}")
    print("-" * 60)
    print(f"Role: {character.role or 'Unknown'}")
    print(f"Gender: {character.gender or 'Unknown'}")
    
    if character.name_variants:
        variants = [v for v in character.name_variants if v != name]
        if variants:
            print("\nName variations:")
            for variant in variants:
                print(f"  - {variant}")
    
    # Group mentions by type
    mention_groups = {}
    for mention in character.mentions:
        mention_groups.setdefault(mention.mention_type, []).append(mention)
    
    print(f"\nTotal mentions: {len(character.mentions)}")
    for mention_type, mentions in mention_groups.items():
        print_mention_group(mentions, mention_type)
    
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
    
    # Determine analysis file path
    analysis_file = Path(input_file).with_suffix('.characters.json')
    characters = {}
    
    # Try to load existing analysis
    if analysis_file.exists():
        print(f"\nLoading existing character analysis from {analysis_file}")
        characters = load_character_analysis(str(analysis_file))
    
    # Perform new analysis if needed
    if not characters:
        print("\nPerforming character analysis...")
        characters = find_characters(content)
        save_character_analysis(characters, str(analysis_file))
        print(f"Analysis saved to {analysis_file}")
    
    # Display results
    print(f"\nFound {len(characters)} characters:")
    for name, character in characters.items():
        print_character_info(name, character)

if __name__ == "__main__":
    main()
