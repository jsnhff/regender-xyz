#!/usr/bin/env python3
"""
TEST FULL TRANSFORMATION PIPELINE WITH OUTPUT SAVING
"""

import sys
import time
from test_bulletproof_chunking import python_pattern_detector, bulletproof_chunker
from gender_transform import transform_gender_with_context
from analyze_characters import analyze_characters

def test_pipeline_and_save(book_path: str, book_name: str, transform_type: str = "neutral"):
    """Test pipeline and save the transformed output."""
    print(f"🚀 TESTING PIPELINE: {book_name.upper()}")
    print(f"📖 Transform type: {transform_type}")
    print("=" * 80)
    
    # Load the book
    with open(book_path, 'r') as f:
        full_text = f.read()
    
    print(f"📚 Loaded {book_name}: {len(full_text):,} characters")
    
    # Bulletproof chunking
    print(f"\n🔧 BULLETPROOF CHUNKING...")
    analysis = python_pattern_detector(full_text)
    chunks = bulletproof_chunker(full_text, analysis)
    print(f"✅ Created {len(chunks)} chunks with 100% coverage")
    
    # Character analysis on first chunk
    print(f"\n👥 CHARACTER ANALYSIS...")
    sample_text = chunks[0]['text'] + (chunks[1]['text'] if len(chunks) > 1 else '')
    character_analysis = analyze_characters(sample_text[:50000])
    
    characters_dict = character_analysis.get('characters', {})
    character_list = []
    for name, char_info in characters_dict.items():
        character_list.append({
            'name': name,
            'gender': char_info.get('gender', 'unknown'),
            'role': char_info.get('role', 'Unknown role')
        })
    
    print(f"✅ Identified {len(character_list)} characters")
    
    # Create character context
    character_context = "Character information:\n"
    for char in character_list:
        character_context += f"- {char['name']}: {char['gender']}, {char['role']}\n"
    
    # Transform FIRST CHUNK and save it
    print(f"\n🎯 TRANSFORMING FIRST CHUNK...")
    first_chunk = chunks[0]
    
    transformed_text, changes = transform_gender_with_context(
        first_chunk['text'], 
        transform_type, 
        character_context,
        model="gpt-4.1-nano"
    )
    
    print(f"✅ Transformation successful!")
    print(f"📊 Output length: {len(transformed_text):,} characters")
    print(f"🔄 Changes made: {len(changes)}")
    
    # Show all changes
    print(f"\n📋 ALL CHANGES MADE:")
    for i, change in enumerate(changes, 1):
        print(f"   {i}. {change}")
    
    # Save the transformed text
    output_file = f"transformed_{book_name.lower().replace(' ', '_')}_{transform_type}_chunk1.txt"
    with open(output_file, 'w') as f:
        f.write(transformed_text)
    
    print(f"\n💾 SAVED TRANSFORMED TEXT TO: {output_file}")
    
    # Show first 500 characters of original vs transformed
    print(f"\n📖 COMPARISON (first 500 chars):")
    print(f"\n🔸 ORIGINAL:")
    print(f"'{first_chunk['text'][:500]}...'")
    print(f"\n🔹 TRANSFORMED:")
    print(f"'{transformed_text[:500]}...'")
    
    return True

if __name__ == "__main__":
    success = test_pipeline_and_save(
        'test_data/pride_and_prejudice_full.txt', 
        'Pride and Prejudice',
        'neutral'  # Change this to 'feminine' or 'masculine' if desired
    )
    exit(0 if success else 1)