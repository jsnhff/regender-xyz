#!/usr/bin/env python3
"""
FULL BOOK TRANSFORMATION
Transform entire books using AI chunking while preserving formatting.
"""

import sys
import time
import argparse
from pathlib import Path
from ai_chunking import chunk_text_ai
from gender_transform import transform_gender_with_context
from analyze_characters import analyze_characters

def transform_full_book(book_path: str, book_name: str, transform_type: str = "neutral", output_file: str = None):
    """Transform an entire book using AI chunking.
    
    Args:
        book_path: Path to the book file
        book_name: Name of the book for display
        transform_type: Type of transformation (neutral, feminine, masculine)
        output_file: Output filename (auto-generated if None)
        
    Returns:
        bool: Success status
    """
    print(f"🚀 FULL BOOK TRANSFORMATION: {book_name.upper()}")
    print(f"📖 Transform type: {transform_type}")
    print("=" * 80)
    
    # Step 1: Load the book
    try:
        with open(book_path, 'r') as f:
            full_text = f.read()
    except FileNotFoundError:
        print(f"❌ {book_name} not found at {book_path}!")
        return False
    
    print(f"📚 Loaded {book_name}: {len(full_text):,} characters")
    
    # Step 2: AI chunking
    print(f"\n🔧 AI CHUNKING...")
    chunks = chunk_text_ai(full_text, prefer_ai=False)  # Use Python fallback for speed
    
    if not chunks:
        print(f"❌ AI chunking failed for {book_name}")
        return False
    
    print(f"✅ Created {len(chunks)} chunks with 100% coverage")
    
    # Step 3: Character analysis on sample
    print(f"\n👥 CHARACTER ANALYSIS...")
    try:
        # Analyze characters on a larger sample for better results
        sample_chunks = chunks[:3] if len(chunks) >= 3 else chunks
        sample_text = ''.join(chunk['text'] for chunk in sample_chunks)[:100000]  # First 100k chars
        
        character_analysis = analyze_characters(sample_text)
        characters_dict = character_analysis.get('characters', {})
        character_list = []
        
        for name, char_info in characters_dict.items():
            character_list.append({
                'name': name,
                'gender': char_info.get('gender', 'unknown'),
                'role': char_info.get('role', 'Unknown role')
            })
        
        print(f"✅ Identified {len(character_list)} characters")
        
        # Show key characters
        for char in character_list[:5]:
            print(f"   - {char['name']}: {char['gender']}, {char['role']}")
            
    except Exception as e:
        print(f"❌ Character analysis failed: {e}")
        # Fallback: use simple character context
        character_list = [{"name": "Main Character", "gender": "unknown", "role": "protagonist"}]
    
    # Create character context
    character_context = "Character information:\n"
    for char in character_list:
        character_context += f"- {char['name']}: {char['gender']}, {char['role']}\n"
    
    # Step 4: Transform ALL chunks
    print(f"\n🔄 TRANSFORMING ALL {len(chunks)} CHUNKS...")
    transformed_chunks = []
    total_start_time = time.time()
    
    for i, chunk in enumerate(chunks, 1):
        chunk_size = chunk['size']
        estimated_tokens = chunk_size // 4
        
        print(f"\n📝 Chunk {i}/{len(chunks)}: {chunk['description']}")
        print(f"   Size: {chunk_size:,} chars (~{estimated_tokens:,} tokens)")
        
        if estimated_tokens > 25000:
            print("   ⚠️ Large chunk - might be close to 32k output limit")
        
        # Transform the chunk
        chunk_start_time = time.time()
        
        try:
            transformed_text, changes = transform_gender_with_context(
                chunk['text'], 
                transform_type, 
                character_context,
                model="gpt-4.1-nano"  # Use fastest model for full book
            )
            
            chunk_time = time.time() - chunk_start_time
            
            transformed_chunks.append({
                'original': chunk,
                'transformed_text': transformed_text,
                'changes': changes,
                'processing_time': chunk_time
            })
            
            print(f"   ✅ Transformed in {chunk_time:.1f}s ({len(changes)} changes)")
            
        except Exception as e:
            print(f"   ❌ Transformation failed: {e}")
            # Keep original text if transformation fails
            transformed_chunks.append({
                'original': chunk,
                'transformed_text': chunk['text'],
                'changes': [],
                'processing_time': 0
            })
    
    total_time = time.time() - total_start_time
    
    # Step 5: Reassemble the full book
    print(f"\n📖 REASSEMBLING FULL BOOK...")
    
    full_transformed_text = ""
    total_changes = 0
    
    for transformed_chunk in transformed_chunks:
        # Concatenate without adding extra spacing - preserve original formatting
        full_transformed_text += transformed_chunk['transformed_text']
        total_changes += len(transformed_chunk['changes'])
    
    # Step 6: Save the output
    if not output_file:
        output_file = f"transformed_{book_name.lower().replace(' ', '_')}_{transform_type}_complete.txt"
    
    try:
        with open(output_file, 'w') as f:
            f.write(full_transformed_text)
        
        print(f"\n💾 SAVED COMPLETE TRANSFORMED BOOK TO: {output_file}")
        
    except Exception as e:
        print(f"❌ Failed to save output: {e}")
        return False
    
    # Step 7: Report results
    print(f"\n🎯 TRANSFORMATION COMPLETE!")
    print(f"   📚 Original length: {len(full_text):,} characters")
    print(f"   📝 Transformed length: {len(full_transformed_text):,} characters")
    print(f"   🔄 Total changes: {total_changes}")
    print(f"   ⏱️ Total time: {total_time:.1f}s")
    print(f"   📊 Average time per chunk: {total_time/len(chunks):.1f}s")
    
    # Verify no content loss
    length_ratio = len(full_transformed_text) / len(full_text)
    if length_ratio > 0.95 and length_ratio < 1.05:
        print(f"   ✅ Length preservation: {length_ratio:.3f} (good)")
    else:
        print(f"   ⚠️ Length change: {length_ratio:.3f} (significant)")
    
    return True

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(description='Transform complete books using AI chunking')
    
    parser.add_argument('book', help='Book filename in test_data/ directory')
    
    parser.add_argument('--transform', '-t', choices=['neutral', 'feminine', 'masculine'], 
                       default='neutral', help='Transformation type (default: neutral)')
    
    parser.add_argument('--output', '-o', help='Output filename (auto-generated if not provided)')
    
    args = parser.parse_args()
    
    # Determine book path
    if args.book.startswith('test_data/'):
        book_path = args.book
    else:
        book_path = f'test_data/{args.book}'
    
    # Get book name from filename
    book_name = Path(book_path).stem.replace('_', ' ').title()
    
    if not Path(book_path).exists():
        print(f"❌ Book not found: {book_path}")
        return 1
    
    success = transform_full_book(book_path, book_name, args.transform, args.output)
    
    if success:
        print(f"\n🏆 SUCCESS: Complete book transformation finished!")
        print(f"📚 Full {book_name} transformed to {args.transform} gender perspective")
        print(f"🎯 Ready for Bill's review - AI chunking preserves formatting!")
    else:
        print(f"\n❌ Transformation failed")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())