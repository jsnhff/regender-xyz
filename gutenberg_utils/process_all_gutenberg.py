#!/usr/bin/env python3
"""
Process all 100 Gutenberg books to clean JSON format using the new modular parser.
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from book_to_json import process_book_to_json


def process_all_books(input_dir="gutenberg_texts", output_dir="gutenberg_json", limit=None):
    """Process all books in the input directory to JSON format."""
    
    # Get all .txt files
    input_path = Path(input_dir)
    txt_files = sorted(list(input_path.glob("*.txt")))
    
    if limit:
        txt_files = txt_files[:limit]
    
    # Statistics
    stats = {
        'total': len(txt_files),
        'successful': 0,
        'failed': 0,
        'total_chapters': 0,
        'total_sentences': 0,
        'total_words': 0
    }
    
    print(f"\nProcessing {len(txt_files)} books...")
    print("-" * 70)
    
    for i, txt_file in enumerate(txt_files, 1):
        # Generate output filename
        output_file = Path(output_dir) / f"{txt_file.stem}_clean.json"
        
        print(f"\n[{i}/{len(txt_files)}] Processing: {txt_file.name}")
        
        try:
            # Process the book
            book_data = process_book_to_json(
                str(txt_file),
                str(output_file),
                verbose=False
            )
            
            # Update statistics
            stats['successful'] += 1
            stats['total_chapters'] += book_data['statistics']['total_chapters']
            stats['total_sentences'] += book_data['statistics']['total_sentences']
            stats['total_words'] += book_data['statistics']['total_words']
            
            print(f"✓ Success: {book_data['statistics']['total_chapters']} chapters, "
                  f"{book_data['statistics']['total_sentences']:,} sentences")
            
        except Exception as e:
            stats['failed'] += 1
            print(f"✗ Failed: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("PROCESSING SUMMARY")
    print("=" * 70)
    print(f"Total books: {stats['total']}")
    print(f"Successful: {stats['successful']} ({stats['successful']/stats['total']*100:.1f}%)")
    print(f"Failed: {stats['failed']}")
    
    return stats


def main():
    """Process all Gutenberg books to JSON."""
    input_dir = "gutenberg_texts"
    output_dir = "gutenberg_json"
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    print("=" * 70)
    print("GUTENBERG BOOKS TO JSON CONVERSION")
    print("=" * 70)
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print("=" * 70)
    
    # Start timer
    start_time = time.time()
    
    # Process all books
    stats = process_all_books(
        input_dir=input_dir,
        output_dir=output_dir,
        limit=None  # Process all books
    )
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Print final summary
    print("\n" + "=" * 70)
    print("CONVERSION COMPLETE")
    print("=" * 70)
    print(f"Time elapsed: {elapsed_time:.1f} seconds")
    print(f"Average time per book: {elapsed_time/stats['total']:.1f} seconds")
    
    if stats['successful'] > 0:
        print(f"\nAverage chapters per book: {stats['total_chapters']/stats['successful']:.1f}")
        print(f"Average sentences per book: {stats['total_sentences']/stats['successful']:.0f}")
        print(f"Average words per book: {stats['total_words']/stats['successful']:.0f}")


if __name__ == "__main__":
    main()