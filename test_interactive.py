#!/usr/bin/env python3
"""
Simple test script to demonstrate the interactive character selection
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.character import CharacterAnalysis
import json

def test_interactive_simulation():
    """Test the interactive system with simulated input"""
    
    # Load the character analysis file
    char_file = Path("books/json/pg1080-A_Modest_Proposal-characters.json")
    
    if not char_file.exists():
        print(f"Character analysis file not found: {char_file}")
        return False
        
    with open(char_file, 'r', encoding='utf-8') as f:
        char_data = json.load(f)
    
    # Convert to CharacterAnalysis object
    characters = CharacterAnalysis.from_dict(char_data)
    
    print("🎭 INTERACTIVE CHARACTER SELECTION DEMO")
    print("=" * 50)
    print(f"\nLoaded {len(characters.characters)} characters from A Modest Proposal")
    
    # Group characters by importance
    main_chars = [c for c in characters.characters if c.importance == "main"]
    supporting_chars = [c for c in characters.characters if c.importance == "supporting"]  
    minor_chars = [c for c in characters.characters if c.importance == "minor"]
    
    print(f"\n📚 MAIN CHARACTERS ({len(main_chars)}):")
    for i, char in enumerate(main_chars, 1):
        print(f"  {i}. {char.name} ({char.gender.value})")
    
    print(f"\n👥 SUPPORTING CHARACTERS ({len(supporting_chars)}):")
    for i, char in enumerate(supporting_chars, len(main_chars) + 1):
        print(f"  {i}. {char.name} ({char.gender.value})")
        
    print(f"\n🎭 MINOR CHARACTERS ({len(minor_chars)}):")
    for i, char in enumerate(minor_chars, len(main_chars) + len(supporting_chars) + 1):
        print(f"  {i}. {char.name} ({char.gender.value})")
    
    print("\n🎯 SIMULATED USER INTERACTION:")
    print("User selects: 1 12 13 (Narrator, Plump girl of fifteen, Narrator's Wife)")
    print("Transform Narrator to female named 'Eleanor'")
    print("Transform Plump girl to male named 'Paul'")
    print("Keep Narrator's Wife unchanged")
    
    # Simulate the mappings that would be created
    custom_mappings = {
        'Narrator': {
            'original_gender': characters.characters[1].gender,  # Main narrator
            'new_gender': 'female',
            'original_name': 'Narrator',
            'new_name': 'Eleanor',
            'pronouns': {'subject': 'she', 'object': 'her', 'possessive': 'her'}
        },
        'Plump girl of fifteen': {
            'original_gender': 'female',
            'new_gender': 'male', 
            'original_name': 'Plump girl of fifteen',
            'new_name': 'Young man of fifteen',
            'pronouns': {'subject': 'he', 'object': 'him', 'possessive': 'his'}
        }
    }
    
    print(f"\n✅ RESULT: {len(custom_mappings)} character transformations configured:")
    for char_name, mapping in custom_mappings.items():
        print(f"  • {mapping['original_name']} → {mapping['new_name']} ({mapping['original_gender']} → {mapping['new_gender']})")
    
    print("\n🚀 NEXT STEPS:")
    print("- Character mappings would be passed to transform service")
    print("- Text would be processed with custom transformations")
    print("- Result would be saved to output file")
    
    return True

if __name__ == '__main__':
    success = test_interactive_simulation()
    print(f"\n{'✅ Test successful!' if success else '❌ Test failed!'}")