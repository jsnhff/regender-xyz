#!/usr/bin/env python3
"""
Utility function for character-based transformation.

This would be added to book_transform/utils.py when integrating the feature.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from book_transform import transform_book
import book_characters.analyzer as char_analyzer


def transform_with_characters(
    book_data: Dict[str, Any],
    character_file: str,
    transform_type: str = 'comprehensive',
    model: str = 'gpt-4o-mini',
    provider: Optional[str] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Transform a book using pre-analyzed character data.
    
    Args:
        book_data: The book data to transform
        character_file: Path to JSON file containing character analysis
        transform_type: Type of transformation to apply
        model: Model to use for transformation
        provider: LLM provider to use
        verbose: Whether to print progress
    
    Returns:
        Transformed book data with metadata about character source
    """
    if not Path(character_file).exists():
        raise FileNotFoundError(f"Character file not found: {character_file}")
    
    # Load character data
    with open(character_file, 'r') as f:
        character_data = json.load(f)
    
    # Extract characters (handle different formats)
    if 'characters' in character_data:
        characters = character_data['characters']
        context = character_data.get('context', '')
    else:
        # Assume the whole file is the character dict
        characters = character_data
        context = char_analyzer.create_character_context(characters)
    
    # Override the character analyzer temporarily
    original_analyze = char_analyzer.analyze_book_characters
    
    def mock_analyze(book_data, model=None, provider=None, sample_size=None, verbose=True):
        """Return pre-loaded characters instead of analyzing."""
        if verbose:
            print(f"✅ Using pre-analyzed characters from: {character_file}")
            print(f"  Loaded {len(characters)} characters")
            
            # Show summary of characters
            male_count = sum(1 for c in characters.values() if c.get('gender') == 'male')
            female_count = sum(1 for c in characters.values() if c.get('gender') == 'female')
            other_count = len(characters) - male_count - female_count
            
            print(f"  Gender distribution: {male_count} male, {female_count} female, {other_count} other")
            
            # Show top characters
            sorted_chars = sorted(
                [(name, info) for name, info in characters.items() 
                 if isinstance(info.get('mentions'), (int, list))],
                key=lambda x: x[1].get('mentions') if isinstance(x[1].get('mentions'), int) 
                            else len(x[1].get('mentions', [])),
                reverse=True
            )[:5]
            
            if sorted_chars:
                print("  Top characters:")
                for name, info in sorted_chars:
                    mentions = info.get('mentions', 0)
                    if isinstance(mentions, list):
                        mentions = len(mentions)
                    print(f"    - {name}: {mentions} mentions ({info.get('gender', 'unknown')})")
        
        return characters, context
    
    # Patch the analyzer
    char_analyzer.analyze_book_characters = mock_analyze
    
    try:
        # Run transformation
        result = transform_book(
            book_data,
            transform_type=transform_type,
            model=model,
            provider=provider,
            verbose=verbose
        )
        
        # Add metadata about character source
        if 'metadata' not in result:
            result['metadata'] = {}
            
        result['metadata']['character_analysis'] = {
            'method': 'pre-loaded',
            'source': character_file,
            'character_count': len(characters)
        }
        
        # If the character file had metadata, include relevant parts
        if 'metadata' in character_data:
            result['metadata']['character_analysis']['original_analysis'] = character_data['metadata']
        
        return result
        
    finally:
        # Always restore the original analyzer
        char_analyzer.analyze_book_characters = original_analyze


def create_all_female_mapping(character_file: str, output_file: str):
    """
    Create a character mapping where all characters are set to female.
    
    This is useful for testing the maximum transformation effect.
    """
    with open(character_file, 'r') as f:
        data = json.load(f)
    
    # Extract characters
    if 'characters' in data:
        characters = data['characters']
    else:
        characters = data
    
    # Create all-female version
    female_characters = {}
    
    for name, info in characters.items():
        # Skip generic terms
        if name in {'They', 'Something', 'Someone', 'Everyone', 'Anyone', 'Nobody', 'People',
                    'Stone', 'King', 'Devil', 'Sorcerer'}:
            continue
        
        female_info = {
            'name': info['name'],
            'gender': 'female',
            'role': info.get('role', f"Character with {info.get('mentions', 0)} mentions"),
            'mentions': info.get('mentions', []),
            'name_variants': info.get('variants', info.get('name_variants', []))
        }
        
        female_characters[name] = female_info
    
    # Save the mapping
    output_data = {
        'metadata': {
            'source': character_file,
            'transformation': 'all_female',
            'character_count': len(female_characters)
        },
        'characters': female_characters
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Created all-female character mapping: {output_file}")
    print(f"  Total characters: {len(female_characters)}")
    
    return female_characters


if __name__ == '__main__':
    print("📋 Character-based Transformation Utilities")
    print("\nThis module provides utilities for transforming books using pre-analyzed character data.")
    print("\nKey functions:")
    print("  - transform_with_characters(): Transform using character file")
    print("  - create_all_female_mapping(): Create test mapping with all female characters")
    print("\nThese functions will be integrated into book_transform/utils.py")