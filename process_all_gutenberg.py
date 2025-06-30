#!/usr/bin/env python3
"""
Process all 100 Gutenberg books to clean JSON format.
"""

import os
import time
from pathlib import Path
from book_to_clean_json import process_all_books


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
    
    print(f"\nOutput files saved to: {os.path.abspath(output_dir)}/")
    
    # List some sample outputs
    output_path = Path(output_dir)
    json_files = list(output_path.glob("*.json"))[:5]
    if json_files:
        print("\nSample output files:")
        for f in json_files:
            size_kb = f.stat().st_size / 1024
            print(f"  - {f.name} ({size_kb:.1f} KB)")
    
    print("\nAll books have been converted to clean JSON format!")
    print("Ready for gender transformation processing.")


if __name__ == "__main__":
    main()