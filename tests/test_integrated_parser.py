#!/usr/bin/env python3
"""Test the integrated parser."""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parsers.parser import IntegratedParser, parse_book


def test_book_detailed(book_path: str):
    """Test integrated parser on a book."""
    book_name = os.path.basename(book_path)
    print(f"\n{'='*60}")
    print(f"Testing: {book_name}")
    print('='*60)
    
    # Parse the book
    result = parse_book(book_path)
    
    # Show metadata
    print(f"\nTitle: {result.title}")
    print(f"Author: {result.author}")
    print(f"Format: {result.format.value} ({result.format_confidence:.0f}% confidence)")
    print(f"Raw text: {result.raw_text_length:,} chars")
    print(f"Cleaned text: {result.cleaned_text_length:,} chars")
    print(f"Reduction: {100 * (1 - result.cleaned_text_length/result.raw_text_length):.1f}%")
    
    # Show structure
    print(f"\nChapters: {len(result.chapters)}")
    
    # Show first few chapters
    print("\nFirst 3 chapters:")
    for chapter in result.chapters[:3]:
        hierarchy = " > ".join(chapter.get('hierarchy', []))
        if hierarchy:
            print(f"  Ch {chapter['number']}: [{hierarchy}] {chapter['title']}")
        else:
            print(f"  Ch {chapter['number']}: {chapter['title']}")
        print(f"    Paragraphs: {len(chapter['paragraphs'])}")
        if chapter['paragraphs']:
            first_para = chapter['paragraphs'][0]
            if len(first_para) > 100:
                print(f"    First para: \"{first_para[:100]}...\"")
            else:
                print(f"    First para: \"{first_para}\"")
    
    # Check for content
    total_paragraphs = sum(len(ch['paragraphs']) for ch in result.chapters)
    print(f"\nTotal paragraphs: {total_paragraphs}")
    
    # Calculate average chapter length
    if result.chapters:
        avg_paras = total_paragraphs / len(result.chapters)
        print(f"Average paragraphs per chapter: {avg_paras:.1f}")


def test_json_output(book_path: str, output_path: str):
    """Test JSON serialization of parsed book."""
    result = parse_book(book_path)
    
    # Convert to JSON-serializable format
    book_json = {
        'title': result.title,
        'author': result.author,
        'metadata': result.metadata,
        'format': result.format.value,
        'format_confidence': result.format_confidence,
        'chapters': result.chapters
    }
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(book_json, f, indent=2, ensure_ascii=False)
    
    print(f"Saved JSON to {output_path}")
    
    # Verify it's valid
    with open(output_path, 'r', encoding='utf-8') as f:
        loaded = json.load(f)
    
    print(f"JSON validation: {len(loaded['chapters'])} chapters loaded")


def main():
    """Test with sample books."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    test_books = [
        os.path.join(base_dir, "books/texts/pg1184-The_Count_of_Monte_Cristo.txt"),
        os.path.join(base_dir, "books/texts/pg11-Alice's_Adventures_in_Wonderland.txt"),
    ]
    
    for book_path in test_books:
        if os.path.exists(book_path):
            test_book_detailed(book_path)
            
            # Test JSON output for first book
            if book_path == test_books[0]:
                output_path = os.path.join(base_dir, "books/json/monte_cristo_parsed.json")
                test_json_output(book_path, output_path)
        else:
            print(f"Book not found: {book_path}")


if __name__ == "__main__":
    main()