#!/usr/bin/env python3
"""
End-to-end test of the complete book processing pipeline.
Tests downloading, parsing, transforming, and recreating books.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Change to parent directory for proper imports
import os
os.chdir(parent_dir)

from book_parser import recreate_text_from_json
from book_transform import transform_book


def test_alice_transformation():
    """Test transformation of Alice in Wonderland."""
    print("\n" + "="*70)
    print("END-TO-END TEST: Alice in Wonderland Gender Transformation")
    print("="*70)
    
    # Load the parsed JSON
    json_path = Path("books/json/pg11-Alice's_Adventures_in_Wonderland_clean.json")
    if not json_path.exists():
        print("❌ Error: Alice in Wonderland JSON not found")
        return False
    
    with open(json_path, 'r') as f:
        book_data = json.load(f)
    
    print(f"\n📖 Book: {book_data['metadata'].get('title', 'Unknown')}")
    print(f"✍️  Author: {book_data['metadata'].get('author', 'Unknown')}")
    print(f"📊 Statistics:")
    stats = book_data['statistics']
    print(f"   - Chapters: {stats['total_chapters']}")
    print(f"   - Paragraphs: {stats['total_paragraphs']}")
    print(f"   - Sentences: {stats['total_sentences']}")
    print(f"   - Words: {stats['total_words']}")
    
    # Test sentence structure
    print("\n🔍 Testing Paragraph Structure:")
    first_chapter = book_data['chapters'][0]
    print(f"   Chapter 1 has {len(first_chapter['paragraphs'])} paragraphs")
    
    # Check for Mrs./Mr. handling
    print("\n🔍 Testing Abbreviation Handling:")
    found_abbrev = False
    for chapter in book_data['chapters'][:5]:  # Check first 5 chapters
        for para in chapter['paragraphs']:
            for sent in para['sentences']:
                if 'Mrs.' in sent or 'Mr.' in sent:
                    print(f"   ✓ Found abbreviation: ...{sent[max(0, sent.find('M')-10):sent.find('.')+10]}...")
                    found_abbrev = True
                    break
            if found_abbrev:
                break
    
    # Transform a sample chapter
    print("\n🔄 Testing Gender Transformation (Chapter 1 only):")
    sample_chapter = {
        'chapters': [book_data['chapters'][0]],
        'metadata': book_data['metadata']
    }
    
    try:
        # Use local MLX model if available
        provider = 'mlx' if Path('/Users/williambarnes/Models/mlx-community/Mistral-7B-Instruct-v0.3-8bit').exists() else None
        
        transformed = transform_book(
            sample_chapter,
            transform_type='comprehensive',
            model='mistral-7b-instruct' if provider == 'mlx' else 'gpt-4o-mini',
            provider=provider,
            verbose=False,
            dry_run=False
        )
        
        print("   ✓ Transformation successful!")
        
        # Compare a few sentences
        print("\n📝 Sample Transformations:")
        orig_sentences = []
        trans_sentences = []
        
        for i, para in enumerate(sample_chapter['chapters'][0]['paragraphs'][:3]):
            for j, sent in enumerate(para['sentences'][:2]):
                orig_sentences.append(sent)
                if i < len(transformed['chapters'][0]['paragraphs']) and \
                   j < len(transformed['chapters'][0]['paragraphs'][i]['sentences']):
                    trans_sentences.append(transformed['chapters'][0]['paragraphs'][i]['sentences'][j])
        
        for orig, trans in zip(orig_sentences[:5], trans_sentences[:5]):
            if orig != trans:
                print(f"\n   Original:  {orig[:80]}...")
                print(f"   Transform: {trans[:80]}...")
        
    except Exception as e:
        print(f"   ❌ Transformation error: {e}")
        return False
    
    # Test text recreation
    print("\n📄 Testing Text Recreation:")
    output_path = Path("tests/alice_recreated.txt")
    output_path.parent.mkdir(exist_ok=True)
    
    try:
        recreate_text_from_json(str(json_path), str(output_path), verbose=True)
        print("   ✓ Text recreation successful!")
        
        # Check file size
        size = output_path.stat().st_size
        print(f"   📏 Recreated text size: {size:,} bytes")
        
        # Clean up
        output_path.unlink()
        
    except Exception as e:
        import traceback
        print(f"   ❌ Recreation error: {e}")
        print("   Traceback:")
        traceback.print_exc()
        return False
    
    print("\n✅ All tests passed!")
    return True


def main():
    """Run end-to-end tests."""
    print("\n🧪 Running End-to-End Book Processing Tests")
    
    # Test with Alice in Wonderland
    success = test_alice_transformation()
    
    if success:
        print("\n🎉 End-to-end test completed successfully!")
    else:
        print("\n❌ End-to-end test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()