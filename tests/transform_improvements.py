#!/usr/bin/env python3
"""Improved transform with character approach with optimizations."""

import json
import time
from typing import Dict, List, Any
from book_transform import transform_book
from book_transform.character_analyzer import create_character_context
import book_transform.character_analyzer as char_analyzer

def create_targeted_female_characters(character_file: str) -> Dict[str, Any]:
    """Create female character mapping with improved targeting."""
    with open(character_file, 'r') as f:
        data = json.load(f)
    
    female_characters = {}
    
    # Process characters based on importance (mentions)
    for name, info in data['characters'].items():
        # Skip generic terms
        if name in {'They', 'Something', 'Someone', 'Everyone', 'Anyone', 'Nobody', 'People', 
                    'Stone', 'King', 'Devil', 'Sorcerer'}:
            continue
        
        # Create female version with context
        female_info = {
            'name': info['name'],
            'gender': 'female',
            'role': f"Character with {info['mentions']} mentions",
            'mentions': [],  # Empty for efficiency
            'name_variants': info.get('variants', [])
        }
        
        # Add specific transformation hints for key characters
        if name == 'Harry Potter':
            female_info['role'] = "Main protagonist, young witch"
            female_info['transform_hints'] = {
                'pronouns': {'he': 'she', 'him': 'her', 'his': 'her'},
                'titles': {'boy': 'girl', 'Mr.': 'Ms.'}
            }
        elif name == 'Dudley':
            female_info['name'] = 'Daisy'  # Common transformation
            female_info['role'] = "Harry's cousin"
        elif name in ['Uncle Vernon', 'Mr. Dursley']:
            female_info['transform_hints'] = {
                'titles': {'Uncle': 'Aunt', 'Mr.': 'Ms.'}
            }
        
        female_characters[name] = female_info
    
    return female_characters


def optimize_transformation(book_file: str, character_file: str, output_prefix: str):
    """Run optimized transformation with character approach."""
    
    print("🚀 Optimized Transform with Character Approach\n")
    
    # Load data
    with open(book_file, 'r') as f:
        book_data = json.load(f)
    
    # Create targeted female characters
    female_characters = create_targeted_female_characters(character_file)
    
    print(f"📊 Character Setup:")
    print(f"  Total characters: {len(female_characters)}")
    print(f"  All set to female gender")
    
    # Show key transformations
    key_chars = ['Harry Potter', 'Dudley', 'Hagrid', 'Hermione Granger', 'Uncle Vernon']
    print("\n  Key character mappings:")
    for char in key_chars:
        if char in female_characters:
            info = female_characters[char]
            print(f"    {char} → {info['name']} (female)")
    
    # Mock the character analyzer
    original_analyze = char_analyzer.analyze_book_characters
    
    def mock_analyze(book_data, model=None, provider=None, sample_size=None, verbose=True):
        """Return pre-loaded female characters."""
        if verbose:
            print("\n✅ Using pre-analyzed character data")
            print(f"  Skipping character detection (saves API calls)")
        
        context = create_character_context(female_characters)
        return female_characters, context
    
    char_analyzer.analyze_book_characters = mock_analyze
    
    try:
        # Transform with optimizations
        print("\n🔄 Starting transformation...")
        start_time = time.time()
        
        # Use smaller chunks for faster processing
        transformed_data = transform_book(
            book_data,
            transform_type='comprehensive',
            model='mistral-7b-instruct',
            provider='mlx',
            verbose=True,
            chunk_size=30  # Smaller chunks for better control
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ Transformation complete in {elapsed:.1f}s")
        
        # Add metadata
        transformed_data['metadata']['transform_approach'] = 'character-based'
        transformed_data['metadata']['transform_note'] = 'All characters transformed to female'
        transformed_data['metadata']['optimization'] = 'Pre-loaded characters, optimized chunking'
        
        # Save outputs
        output_json = f"{output_prefix}.json"
        output_text = f"{output_prefix}.txt"
        
        with open(output_json, 'w') as f:
            json.dump(transformed_data, f, indent=2)
        
        from book_transform.json_to_text import recreate_text_from_json
        recreate_text_from_json(output_json, output_text, verbose=False)
        
        print(f"\n📁 Outputs saved:")
        print(f"  JSON: {output_json}")
        print(f"  Text: {output_text}")
        
        # Summary statistics
        print(f"\n📊 Transformation Summary:")
        print(f"  Chapters: {len(transformed_data['chapters'])}")
        print(f"  Changes: {len(transformed_data.get('changes', []))}")
        print(f"  Characters: {len(female_characters)}")
        print(f"  Time: {elapsed:.1f}s")
        
        # Quality check
        if 'changes' in transformed_data and transformed_data['changes']:
            print(f"\n🔍 Sample transformations:")
            for i, change in enumerate(transformed_data['changes'][:3]):
                print(f"\n  Example {i+1}:")
                print(f"    Original: \"{change.get('original', '')[:60]}...\"")
                print(f"    Transformed: \"{change.get('transformed', '')[:60]}...\"")
        
    finally:
        # Restore original
        char_analyzer.analyze_book_characters = original_analyze


def batch_transform_chapters(book_file: str, character_file: str, chapters: List[int] = None):
    """Transform specific chapters for testing."""
    
    with open(book_file, 'r') as f:
        book_data = json.load(f)
    
    if chapters is None:
        chapters = [0, 1, 2]  # First 3 chapters by default
    
    # Create subset
    test_data = {
        'metadata': book_data['metadata'],
        'chapters': [book_data['chapters'][i] for i in chapters if i < len(book_data['chapters'])]
    }
    
    # Save test subset
    test_file = 'test_chapters.json'
    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)
    
    # Run optimized transformation
    optimize_transformation(test_file, character_file, 'test_chapters_female')


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Test mode - just first 3 chapters
        print("🧪 Test Mode: Transforming first 3 chapters\n")
        batch_transform_chapters(
            'books/json/Sorcerers_Stone_clean.json',
            'books/json/Sorcerers_Stone_clean_characters.json',
            [0, 1, 2]
        )
    else:
        # Full book transformation
        optimize_transformation(
            'books/json/Sorcerers_Stone_clean.json',
            'books/json/Sorcerers_Stone_clean_characters.json',
            'books/output/Sorcerers_Stone_female_optimized'
        )