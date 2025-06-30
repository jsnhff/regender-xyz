#!/usr/bin/env python3
"""
book_to_json.py - Convert books to clean JSON format

This module uses the modular book parser to convert text books into JSON format with:
- Chapter/section detection (supports 100+ formats)
- Clean sentence splitting
- Metadata extraction
- Support for international languages and plays

Usage:
    from book_to_json import process_book_to_json
    
    # Process a book
    book_data = process_book_to_json("book.txt", "book_clean.json")
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from book_parser import BookParser


def recreate_text_from_json(json_file: str, output_file: Optional[str] = None, 
                           verbose: bool = True) -> str:
    """
    Recreate the original text from a clean JSON file.
    
    Args:
        json_file: Path to the JSON file
        output_file: Optional path to save the recreated text
        verbose: Whether to print progress
        
    Returns:
        The recreated text
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        book_data = json.load(f)
    
    # Recreate the text
    parts = []
    for chapter in book_data['chapters']:
        # Add chapter title if present
        if chapter.get('title'):
            parts.append(f"\n{chapter['title']}\n")
        elif chapter.get('number'):
            # Reconstruct chapter header based on type
            chapter_type = chapter.get('type', 'chapter')
            number = chapter['number']
            if chapter_type == 'chapter':
                parts.append(f"\nCHAPTER {number}\n")
            elif chapter_type == 'act':
                parts.append(f"\nACT {number}\n")
            elif chapter_type == 'scene':
                parts.append(f"\nSCENE {number}\n")
            else:
                parts.append(f"\n{chapter_type.upper()} {number}\n")
        
        # Add sentences with proper spacing
        chapter_text = ' '.join(chapter['sentences'])
        
        # Restore paragraph breaks where we have \n\n in sentences
        chapter_text = chapter_text.replace('\\n\\n', '\n\n')
        
        parts.append(chapter_text)
    
    recreated_text = '\n'.join(parts)
    
    # Save if requested
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(recreated_text)
        if verbose:
            print(f"✓ Recreated text saved to: {output_file}")
    
    return recreated_text


def process_book_to_json(input_file: str, output_file: Optional[str] = None, 
                        verbose: bool = True) -> Dict[str, Any]:
    """
    Process a book file to JSON format using the modular parser
    
    Args:
        input_file: Path to input text file
        output_file: Path to output JSON file (optional)
        verbose: Whether to print progress messages
        
    Returns:
        Dictionary containing the processed book data
    """
    # Create parser
    parser = BookParser()
    
    # Print info if verbose
    if verbose:
        print(f"Processing: {input_file}")
    
    try:
        # Parse the book
        book_data = parser.parse_file(input_file)
        
        # Save to file if output path provided
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(book_data, f, indent=2, ensure_ascii=False)
            
            if verbose:
                stats = book_data['statistics']
                print(f"✓ Processed {stats['total_chapters']} chapters")
                print(f"  Total sentences: {stats['total_sentences']:,}")
                print(f"  Total words: {stats['total_words']:,}")
                print(f"  Output: {output_file}")
        
        return book_data
        
    except Exception as e:
        if verbose:
            print(f"✗ Error processing {input_file}: {str(e)}")
        raise


def main():
    """Command line interface for testing"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python book_to_json.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    process_book_to_json(input_file, output_file)


if __name__ == "__main__":
    main()