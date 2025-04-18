#!/usr/bin/env python3
"""
Interactive CLI module for regender-xyz.
Provides interactive features for the command-line interface.
"""

import json
import sys
from typing import Dict, List, Optional, Any

def prompt_yes_no(question: str) -> bool:
    """Prompt the user for a yes/no response.
    
    Args:
        question: The question to ask
        
    Returns:
        True for yes, False for no
    """
    while True:
        response = input(f"{question} (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'.")

def get_character_customizations(characters: List[Dict[str, Any]]) -> Dict[str, str]:
    """Interactively get character name customizations from the user.
    
    Args:
        characters: List of character dictionaries from analysis
        
    Returns:
        Dictionary mapping original character names to custom names
    """
    print("\n=== Character Name Customization ===")
    print("You can customize character names for the transformation.")
    print("Press Enter to keep the original name, or type a new name.")
    
    customizations = {}
    
    for char in characters:
        name = char['name']
        gender = char.get('gender', 'unknown')
        mentions = char.get('mentions', 0)
        
        print(f"\n{name} ({gender}, {mentions} mentions)")
        new_name = input(f"New name for {name} [keep as is]: ").strip()
        
        if new_name and new_name != name:
            customizations[name] = new_name
            print(f"✓ {name} will be transformed to {new_name}")
    
    return customizations

def load_characters_from_analysis(analysis_file: str) -> List[Dict[str, Any]]:
    """Load character information from an analysis file.
    
    Args:
        analysis_file: Path to the analysis JSON file
        
    Returns:
        List of character dictionaries
    """
    try:
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis = json.load(f)
        
        if 'characters' in analysis:
            return analysis['characters']
        else:
            print("Error: Analysis file does not contain character information.")
            return []
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading analysis file: {e}")
        return []

def interactive_transformation_setup(analysis_file: Optional[str] = None) -> Dict[str, Any]:
    """Set up an interactive transformation session.
    
    Args:
        analysis_file: Optional path to an analysis file
        
    Returns:
        Dictionary of transformation options
    """
    options = {}
    
    # Character customization (if analysis file provided)
    if analysis_file:
        characters = load_characters_from_analysis(analysis_file)
        if characters:
            if prompt_yes_no("Would you like to customize character names?"):
                options['character_customizations'] = get_character_customizations(characters)
    
    return options

if __name__ == "__main__":
    # Simple test
    print("Interactive CLI Module Test")
    options = interactive_transformation_setup()
    print(f"Options: {options}")
