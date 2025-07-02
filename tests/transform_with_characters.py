#!/usr/bin/env python3
"""Transform book using pre-analyzed character data."""

import json
import sys
import time
from book_transform import transform_book


def create_all_female_characters(character_file: str) -> dict:
    """Load character data and convert all to female."""
    with open(character_file, 'r') as f:
        data = json.load(f)
    
    # Convert all characters to female
    female_characters = {}
    for name, info in data['characters'].items():
        # Skip non-character entries
        if name in {'They', 'Something', 'Someone', 'Everyone', 'Anyone', 'Nobody', 'People'}:
            continue
            
        female_info = {
            'name': info['name'],
            'gender': 'female',  # Force all to female
            'role': f"Character with {info['mentions']} mentions",
            'mentions': [],  # Empty for efficiency
            'name_variants': info.get('variants', [])
        }
        
        female_characters[name] = female_info
    
    print(f"Prepared {len(female_characters)} characters, all set to female gender")
    
    return female_characters


def main():
    """Transform Sorcerer's Stone with all female characters."""
    
    # File paths
    book_file = 'books/json/Sorcerers_Stone_clean.json'
    character_file = 'books/json/Sorcerers_Stone_clean_characters.json'
    output_json = 'books/output/Sorcerers_Stone_all_female.json'
    output_text = 'books/output/Sorcerers_Stone_all_female.txt'
    
    print("📚 Loading book and character data...")
    
    # Load book
    with open(book_file, 'r') as f:
        book_data = json.load(f)
    
    # Create all-female character data
    female_characters = create_all_female_characters(character_file)
    
    # Temporarily patch the character analyzer to return our data
    import book_transform.character_analyzer as char_analyzer
    original_analyze = char_analyzer.analyze_book_characters
    
    def mock_analyze(book_data, model=None, provider=None, sample_size=None, verbose=True):
        """Return our pre-loaded all-female characters."""
        if verbose:
            print("Using pre-analyzed character data (all female)...")
            print(f"  Loaded {len(female_characters)} characters")
            if female_characters:
                char_names = list(female_characters.keys())[:10]
                print(f"  Main characters: {', '.join(char_names)}")
        
        # Create character context
        context = char_analyzer.create_character_context(female_characters)
        return female_characters, context
    
    # Patch the function
    char_analyzer.analyze_book_characters = mock_analyze
    
    try:
        print("\n🔄 Transforming with all female characters...")
        print("🤖 Using MLX with mistral-7b-instruct model")
        
        # Use the standard transform_book function
        start_time = time.time()
        transformed_data = transform_book(
            book_data,
            transform_type='comprehensive',
            model='mistral-7b-instruct',
            provider='mlx',
            verbose=True
        )
        elapsed = time.time() - start_time
        
        print(f"\n✅ Transformation complete in {elapsed:.1f}s")
        
        # Add metadata about the all-female transformation
        transformed_data['metadata']['transform_note'] = 'All characters transformed to female gender'
        transformed_data['metadata']['character_source'] = 'Pre-analyzed from full book scan'
        
        # Save JSON
        with open(output_json, 'w') as f:
            json.dump(transformed_data, f, indent=2)
        print(f"✅ Saved JSON: {output_json}")
        
        # Convert to text
        from book_transform.json_to_text import recreate_text_from_json
        recreate_text_from_json(output_json, output_text, verbose=False)
        print(f"✅ Saved text: {output_text}")
        
        # Summary
        total_changes = len(transformed_data.get('changes', []))
        print(f"\n📊 Transformation Summary:")
        print(f"  Total changes: {total_changes}")
        print(f"  Characters transformed: {len(female_characters)}")
        print(f"  Chapters processed: {len(transformed_data['chapters'])}")
        
        # Show sample changes
        if 'changes' in transformed_data and transformed_data['changes']:
            print(f"\n📝 Sample changes:")
            for change in transformed_data['changes'][:5]:
                orig = change.get('original', '')[:50]
                trans = change.get('transformed', '')[:50]
                print(f"  Chapter {change.get('chapter', '?')}: \"{orig}...\" → \"{trans}...\"")
                
    finally:
        # Restore original function
        char_analyzer.analyze_book_characters = original_analyze


if __name__ == '__main__':
    main()