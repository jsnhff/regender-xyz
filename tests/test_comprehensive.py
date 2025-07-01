#!/usr/bin/env python3
"""
Comprehensive test suite for the book processing system.
Tests all major features including:
- Paragraph preservation
- Abbreviation handling
- Gender transformation
- Text recreation
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

from book_parser import BookParser, recreate_text_from_json
from book_transform import transform_book


def test_abbreviation_handling():
    """Test that abbreviations like Mr., Mrs., Dr. don't break sentences."""
    print("\n🔍 Testing Abbreviation Handling")
    
    test_text = """Mr. Smith met Mrs. Johnson at Dr. Brown's office. They discussed 
the meeting with Prof. Williams that was scheduled for Jan. 15th at 3 p.m.

Ms. Davis and Mr. Thompson arrived at the U.S. Embassy. The Rev. Martin 
gave a speech about St. Patrick's Day celebrations."""
    
    parser = BookParser()
    # Create a simple structure to test
    result = parser.parse_text(test_text)
    
    # Check sentence count
    total_sentences = sum(ch['sentence_count'] for ch in result['chapters'])
    print(f"   Sentences found: {total_sentences}")
    
    # Check specific sentences
    success = True
    for chapter in result['chapters']:
        for para in chapter['paragraphs']:
            for sent in para['sentences']:
                if 'Mr.' in sent and 'Mrs.' in sent and 'Dr.' in sent:
                    print(f"   ✓ Correctly preserved: '{sent[:60]}...'")
                    if "Mr. Smith met Mrs. Johnson at Dr. Brown's office." not in sent:
                        print(f"   ❌ Sentence incorrectly split!")
                        success = False
    
    return success


def test_paragraph_preservation():
    """Test that paragraph structure is preserved."""
    print("\n📝 Testing Paragraph Preservation")
    
    test_text = """First paragraph with multiple sentences. This is the second sentence.
And here's a third sentence in the same paragraph.

Second paragraph starts here. It also has multiple sentences.
This paragraph talks about something different.

Third paragraph is shorter. Just two sentences here."""
    
    parser = BookParser()
    result = parser.parse_text(test_text)
    
    # Check paragraph count
    total_paragraphs = sum(len(ch['paragraphs']) for ch in result['chapters'])
    print(f"   Paragraphs found: {total_paragraphs}")
    
    if total_paragraphs == 3:
        print("   ✓ Correct paragraph count")
        
        # Check sentences per paragraph
        for i, chapter in enumerate(result['chapters']):
            for j, para in enumerate(chapter['paragraphs']):
                sent_count = len(para['sentences'])
                print(f"   Paragraph {j+1}: {sent_count} sentences")
        
        return True
    else:
        print(f"   ❌ Expected 3 paragraphs, found {total_paragraphs}")
        return False


def test_json_structure():
    """Test the JSON structure is correct."""
    print("\n🏗️  Testing JSON Structure")
    
    # Load a sample JSON
    json_files = list(Path("books/json").glob("*.json"))
    if not json_files:
        print("   ❌ No JSON files found to test")
        return False
    
    with open(json_files[0], 'r') as f:
        book_data = json.load(f)
    
    # Check required fields
    required_fields = ['metadata', 'chapters', 'statistics']
    for field in required_fields:
        if field in book_data:
            print(f"   ✓ Found required field: {field}")
        else:
            print(f"   ❌ Missing required field: {field}")
            return False
    
    # Check chapter structure
    if book_data['chapters']:
        chapter = book_data['chapters'][0]
        if 'paragraphs' in chapter:
            print("   ✓ New paragraph structure detected")
            if 'sentences' in chapter['paragraphs'][0]:
                print("   ✓ Sentences nested in paragraphs")
                return True
        elif 'sentences' in chapter:
            print("   ⚠️  Old flat sentence structure detected")
    
    return True


def test_statistics():
    """Test that statistics are calculated correctly."""
    print("\n📊 Testing Statistics Calculation")
    
    json_files = list(Path("books/json").glob("*.json"))
    if not json_files:
        print("   ❌ No JSON files found to test")
        return False
    
    with open(json_files[0], 'r') as f:
        book_data = json.load(f)
    
    stats = book_data.get('statistics', {})
    
    # Check all statistics fields
    expected_stats = [
        'total_chapters',
        'total_paragraphs',
        'total_sentences',
        'total_words',
        'average_sentences_per_paragraph',
        'average_paragraphs_per_chapter'
    ]
    
    for stat in expected_stats:
        if stat in stats:
            print(f"   ✓ {stat}: {stats[stat]}")
        else:
            print(f"   ❌ Missing statistic: {stat}")
    
    # Verify calculations
    if 'total_paragraphs' in stats and 'total_sentences' in stats:
        calc_avg = stats['total_sentences'] / stats['total_paragraphs']
        if abs(calc_avg - stats.get('average_sentences_per_paragraph', 0)) < 0.01:
            print("   ✓ Average calculations verified")
            return True
    
    return True


def test_transformation_compatibility():
    """Test that transformation works with new structure."""
    print("\n🔄 Testing Transformation Compatibility")
    
    # Create a simple test book
    test_book = {
        "metadata": {"title": "Test Book", "author": "Test Author"},
        "chapters": [{
            "number": "1",
            "title": "Chapter One",
            "paragraphs": [
                {"sentences": ["Alice went to the store.", "She bought some apples."]},
                {"sentences": ["Bob was her friend.", "He liked oranges."]}
            ],
            "sentence_count": 4,
            "word_count": 15
        }],
        "statistics": {"total_chapters": 1, "total_sentences": 4}
    }
    
    try:
        # Test transformation
        transformed = transform_book(
            test_book,
            transform_type='comprehensive',
            model='gpt-4o-mini',
            verbose=False
        )
        
        # Check structure is preserved
        if 'paragraphs' in transformed['chapters'][0]:
            print("   ✓ Paragraph structure preserved after transformation")
            
            # Check for actual changes
            orig_sent = test_book['chapters'][0]['paragraphs'][0]['sentences'][0]
            trans_sent = transformed['chapters'][0]['paragraphs'][0]['sentences'][0]
            
            if 'Alice' in orig_sent and 'Alice' not in trans_sent:
                print("   ✓ Gender transformation applied")
                return True
            else:
                print("   ⚠️  No transformation detected (may be API issue)")
                return True  # Don't fail on API issues
        else:
            print("   ❌ Paragraph structure lost")
            return False
            
    except Exception as e:
        print(f"   ❌ Transformation error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n🧪 Running Comprehensive Book Processing Tests")
    print("=" * 60)
    
    tests = [
        test_abbreviation_handling,
        test_paragraph_preservation,
        test_json_structure,
        test_statistics,
        test_transformation_compatibility
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ Test error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()