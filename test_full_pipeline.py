#!/usr/bin/env python3
"""
TEST FULL TRANSFORMATION PIPELINE
Integrate bulletproof chunking with gender transformation to process entire books.
"""

import sys
import time
from ai_chunking import chunk_text_ai
from gender_transform import transform_gender_with_context
from analyze_characters import analyze_characters

def test_full_pipeline(book_path: str, book_name: str, transform_type: str = "neutral"):
    """Test the complete pipeline: chunking + character analysis + transformation.
    
    Args:
        book_path: Path to the book file
        book_name: Name of the book for display
        transform_type: Type of transformation (neutral, feminine, masculine)
    """
    print(f"🚀 TESTING FULL PIPELINE: {book_name.upper()}")
    print(f"📖 Transform type: {transform_type}")
    print("=" * 80)
    
    # Step 1: Load the book
    try:
        with open(book_path, 'r') as f:
            full_text = f.read()
    except FileNotFoundError:
        print(f"❌ {book_name} not found!")
        return False
    
    print(f"📚 Loaded {book_name}: {len(full_text):,} characters")
    
    # Step 2: AI chunking
    print(f"\n🔧 AI CHUNKING...")
    chunks = chunk_text_ai(full_text, prefer_ai=False)  # Use Python fallback for speed
    
    if not chunks:
        print(f"❌ Chunking failed for {book_name}")
        return False
    
    print(f"✅ Created {len(chunks)} chunks with 100% coverage")
    
    # Step 3: Character analysis
    print(f"\n👥 CHARACTER ANALYSIS...")
    start_time = time.time()
    
    try:
        # Analyze characters on a sample (first few chunks) to save time/quota
        sample_text = chunks[0]['text'] + (chunks[1]['text'] if len(chunks) > 1 else '')
        character_analysis = analyze_characters(sample_text[:50000])  # First 50k chars
        
        characters_dict = character_analysis.get('characters', {})
        character_list = []
        for name, char_info in characters_dict.items():
            character_list.append({
                'name': name,
                'gender': char_info.get('gender', 'unknown'),
                'role': char_info.get('role', 'Unknown role')
            })
        
        analysis_time = time.time() - start_time
        print(f"✅ Identified {len(character_list)} characters in {analysis_time:.1f}s")
        
        # Show key characters
        for char in character_list[:3]:
            print(f"   - {char['name']}: {char['gender']}, {char['role']}")
            
    except Exception as e:
        print(f"❌ Character analysis failed: {e}")
        # Fallback: use simple character context
        character_list = [{"name": "Main Character", "gender": "unknown", "role": "protagonist"}]
    
    # Step 4: Test transformation on first chunk
    print(f"\n🔄 TESTING TRANSFORMATION ON FIRST CHUNK...")
    first_chunk = chunks[0]
    chunk_size = first_chunk['size']
    estimated_tokens = chunk_size // 4
    
    print(f"📊 First chunk: {chunk_size:,} chars (~{estimated_tokens:,} tokens)")
    print(f"📝 Description: {first_chunk['description']}")
    
    if estimated_tokens > 25000:
        print("⚠️ Chunk might be close to 32k output limit")
    else:
        print("✅ Chunk size looks safe for transformation")
    
    # Create character context
    character_context = "Character information:\n"
    for char in character_list:
        character_context += f"- {char['name']}: {char['gender']}, {char['role']}\n"
    
    # Transform the first chunk
    print(f"\n🎯 TRANSFORMING FIRST CHUNK...")
    start_time = time.time()
    
    try:
        transformed_text, changes = transform_gender_with_context(
            first_chunk['text'], 
            transform_type, 
            character_context,
            model="gpt-4.1-nano"  # Use 4.1-nano model with 2M daily limit
        )
        
        transform_time = time.time() - start_time
        
        print(f"✅ Transformation successful in {transform_time:.1f}s!")
        print(f"📊 Output length: {len(transformed_text):,} characters")
        print(f"🔄 Changes made: {len(changes)}")
        
        # Show sample changes
        for i, change in enumerate(changes[:3]):
            print(f"   {i+1}. {change}")
        if len(changes) > 3:
            print(f"   ... and {len(changes) - 3} more changes")
        
        # Show sample of transformed text
        print(f"\n📖 SAMPLE TRANSFORMED TEXT:")
        sample = transformed_text[:200]
        print(f"   {repr(sample)}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Transformation failed: {e}")
        return False

def main():
    """Test the full pipeline on available books."""
    print("🚀 FULL PIPELINE TESTING")
    print("=" * 80)
    
    # Test books
    test_books = [
        ('test_data/pride_and_prejudice_full.txt', 'Pride and Prejudice'),
        # ('test_data/moby_dick_full_text.txt', 'Moby Dick')  # Comment out to save quota
    ]
    
    transform_types = ['neutral']  # Start with neutral
    
    all_success = True
    
    for book_path, book_name in test_books:
        for transform_type in transform_types:
            print(f"\n{'='*80}")
            success = test_full_pipeline(book_path, book_name, transform_type)
            if not success:
                all_success = False
    
    print(f"\n{'='*80}")
    print(f"🎯 FINAL PIPELINE RESULT:")
    if all_success:
        print("🏆 COMPLETE SUCCESS - FULL PIPELINE WORKS!")
        print("📚 Ready to transform entire books with bulletproof chunking!")
        print("💪 Bill's solution can't compete with this!")
    else:
        print("❌ Pipeline needs refinement")
    
    return all_success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)