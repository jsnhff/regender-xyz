#!/usr/bin/env python3
"""Test and compare transform with character approach."""

import json
import time
from book_transform import transform_book

def test_single_chapter():
    """Test transformation on a single chapter with pre-loaded characters."""
    
    # Load book data
    with open('books/json/Sorcerers_Stone_clean.json', 'r') as f:
        book_data = json.load(f)
    
    # Load character data
    with open('books/json/Sorcerers_Stone_clean_characters.json', 'r') as f:
        char_data = json.load(f)
    
    # Extract just the first chapter for testing
    test_data = {
        'metadata': book_data['metadata'],
        'chapters': [book_data['chapters'][0]]  # Just chapter 1
    }
    
    print("📊 Character Data Summary:")
    print(f"Total characters: {len(char_data['characters'])}")
    
    # Show top characters
    sorted_chars = sorted(char_data['characters'].items(), 
                         key=lambda x: x[1]['mentions'], 
                         reverse=True)[:10]
    
    print("\nTop 10 characters by mentions:")
    for name, info in sorted_chars:
        print(f"  - {name}: {info['mentions']} mentions ({info['gender']})")
    
    # Test transform with female characters
    print("\n🔄 Testing transform with all-female characters...")
    
    # Create all-female character mapping
    female_chars = {}
    for name, info in char_data['characters'].items():
        if name not in {'They', 'Something', 'Someone', 'Everyone', 'Anyone', 'Nobody', 'People'}:
            female_chars[name] = {
                'name': info['name'],
                'gender': 'female',
                'role': f"Character with {info['mentions']} mentions",
                'mentions': [],
                'name_variants': info.get('variants', [])
            }
    
    print(f"\nPrepared {len(female_chars)} female characters")
    
    # Mock the character analyzer
    import book_transform.character_analyzer as char_analyzer
    original_analyze = char_analyzer.analyze_book_characters
    
    def mock_analyze(book_data, model=None, provider=None, sample_size=None, verbose=True):
        if verbose:
            print("Using pre-loaded female characters...")
        context = char_analyzer.create_character_context(female_chars)
        return female_chars, context
    
    char_analyzer.analyze_book_characters = mock_analyze
    
    try:
        # Transform the chapter
        start = time.time()
        result = transform_book(
            test_data,
            transform_type='comprehensive',
            model='mistral-7b-instruct',
            provider='mlx',
            verbose=True
        )
        elapsed = time.time() - start
        
        print(f"\n✅ Transformation complete in {elapsed:.1f}s")
        
        # Analyze results
        changes = result.get('changes', [])
        print(f"\n📝 Results:")
        print(f"  Total changes: {len(changes)}")
        
        # Show sample changes
        if changes:
            print("\n  Sample changes:")
            for i, change in enumerate(changes[:5]):
                orig = change.get('original', '')[:40]
                trans = change.get('transformed', '')[:40]
                print(f"    {i+1}. \"{orig}...\" → \"{trans}...\"")
        
        # Save output
        output_file = 'test_chapter1_female.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✅ Saved test output to: {output_file}")
        
    finally:
        # Restore original
        char_analyzer.analyze_book_characters = original_analyze


def compare_approaches():
    """Compare standard vs character-based transformation."""
    
    print("\n📊 Comparing transformation approaches...")
    
    # Load first chapter
    with open('books/json/Sorcerers_Stone_clean.json', 'r') as f:
        book_data = json.load(f)
    
    test_data = {
        'metadata': book_data['metadata'],
        'chapters': [book_data['chapters'][0]]
    }
    
    # Test 1: Standard approach (auto character detection)
    print("\n1️⃣ Standard approach (auto character detection):")
    start = time.time()
    standard_result = transform_book(
        test_data,
        transform_type='comprehensive',
        model='mistral-7b-instruct',
        provider='mlx',
        verbose=False
    )
    standard_time = time.time() - start
    
    print(f"  Time: {standard_time:.1f}s")
    print(f"  Changes: {len(standard_result.get('changes', []))}")
    
    # Test 2: Pre-loaded character approach
    print("\n2️⃣ Pre-loaded character approach:")
    
    # Load and prepare characters
    with open('books/json/Sorcerers_Stone_clean_characters.json', 'r') as f:
        char_data = json.load(f)
    
    female_chars = {}
    for name, info in char_data['characters'].items():
        if name not in {'They', 'Something', 'Someone', 'Everyone', 'Anyone', 'Nobody', 'People'}:
            female_chars[name] = {
                'name': info['name'],
                'gender': 'female',
                'role': f"Character with {info['mentions']} mentions",
                'mentions': [],
                'name_variants': info.get('variants', [])
            }
    
    # Mock analyzer
    import book_transform.character_analyzer as char_analyzer
    original_analyze = char_analyzer.analyze_book_characters
    
    def mock_analyze(book_data, model=None, provider=None, sample_size=None, verbose=True):
        context = char_analyzer.create_character_context(female_chars)
        return female_chars, context
    
    char_analyzer.analyze_book_characters = mock_analyze
    
    try:
        start = time.time()
        preloaded_result = transform_book(
            test_data,
            transform_type='comprehensive',
            model='mistral-7b-instruct',
            provider='mlx',
            verbose=False
        )
        preloaded_time = time.time() - start
        
        print(f"  Time: {preloaded_time:.1f}s")
        print(f"  Changes: {len(preloaded_result.get('changes', []))}")
        
        # Compare results
        print(f"\n📊 Comparison:")
        print(f"  Speed improvement: {standard_time/preloaded_time:.1f}x faster")
        print(f"  Character detection skipped, saving API calls")
        
    finally:
        char_analyzer.analyze_book_characters = original_analyze


if __name__ == '__main__':
    print("🧪 Testing Transform with Character Approach\n")
    
    # Test single chapter
    test_single_chapter()
    
    # Compare approaches
    compare_approaches()
    
    print("\n✅ Test complete!")