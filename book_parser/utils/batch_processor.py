#!/usr/bin/env python3
"""
Batch process text books to clean JSON format and generate summary reports.

This module provides batch processing functionality for converting multiple
text files to structured JSON format.
"""

import os
import sys
import time
import json
import statistics
from pathlib import Path
from collections import Counter
from typing import Dict, List, Optional, Tuple

from ..parser import BookParser
from ..formatters import save_book_json, load_book_json


def print_progress(current: int, total: int, prefix: str = "Progress"):
    """Print a simple progress indicator."""
    percentage = (current / total) * 100
    print(f"\r{prefix}: {current}/{total} ({percentage:.1f}%)", end="", flush=True)


def process_all_books(input_dir: str = "books/texts", 
                     output_dir: str = "books/json", 
                     limit: Optional[int] = None,
                     generate_summary: bool = True) -> Dict:
    """
    Process all books in the input directory to JSON format.
    
    Args:
        input_dir: Directory containing text files
        output_dir: Directory to save JSON files
        limit: Optional limit on number of books to process
        generate_summary: Whether to generate a summary report after processing
        
    Returns:
        Dictionary containing processing statistics
    """
    
    # Get all .txt files
    input_path = Path(input_dir)
    txt_files = sorted(list(input_path.glob("*.txt")))
    
    if limit:
        txt_files = txt_files[:limit]
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Statistics
    stats = {
        'total': len(txt_files),
        'successful': 0,
        'failed': 0,
        'total_chapters': 0,
        'total_sentences': 0,
        'total_words': 0,
        'failed_books': []
    }
    
    print(f"\nProcessing {len(txt_files)} books...")
    print("-" * 70)
    
    for i, txt_file in enumerate(txt_files, 1):
        # Generate output filename
        output_file = output_path / f"{txt_file.stem}_clean.json"
        
        print(f"\n[{i}/{len(txt_files)}] Processing: {txt_file.name}")
        
        try:
            # Process the book
            parser = BookParser()
            book_data = parser.parse_file(str(txt_file))
            
            # Save to JSON
            save_book_json(book_data, str(output_file))
            
            # Update statistics
            stats['successful'] += 1
            stats['total_chapters'] += book_data['statistics']['total_chapters']
            stats['total_sentences'] += book_data['statistics']['total_sentences']
            stats['total_words'] += book_data['statistics']['total_words']
            
            print(f"✓ Success: {book_data['statistics']['total_chapters']} chapters, "
                  f"{book_data['statistics']['total_sentences']:,} sentences")
            
        except Exception as e:
            stats['failed'] += 1
            stats['failed_books'].append({
                'file': txt_file.name,
                'error': str(e)
            })
            print(f"✗ Failed: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("PROCESSING SUMMARY")
    print("=" * 70)
    print(f"Total books: {stats['total']}")
    print(f"Successful: {stats['successful']} ({stats['successful']/max(1, stats['total'])*100:.1f}%)")
    print(f"Failed: {stats['failed']}")
    
    # Generate detailed summary report if requested
    if generate_summary and stats['successful'] > 0:
        print("\nGenerating summary report...")
        summary_stats = generate_summary_report(output_dir)
        stats['summary'] = summary_stats
    
    return stats


def generate_summary_report(json_dir: str = "book_json") -> Dict:
    """
    Generate a summary report of all converted books.
    
    Args:
        json_dir: Directory containing JSON files
        
    Returns:
        Dictionary containing summary statistics
    """
    json_path = Path(json_dir)
    json_files = sorted(json_path.glob("*.json"))
    
    # Collect statistics
    stats = {
        'total_files': len(json_files),
        'books_with_chapters': 0,
        'books_without_chapters': 0,
        'chapter_counts': [],
        'sentence_counts': [],
        'word_counts': [],
        'titles': [],
        'problematic_books': []
    }
    
    print("Analyzing JSON files...")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract statistics
            chapter_count = data['statistics']['total_chapters']
            sentence_count = data['statistics']['total_sentences']
            word_count = data['statistics']['total_words']
            title = data['metadata'].get('title', 'Unknown')
            
            stats['titles'].append((json_file.stem, title, chapter_count))
            
            if chapter_count > 0:
                stats['books_with_chapters'] += 1
                stats['chapter_counts'].append(chapter_count)
            else:
                stats['books_without_chapters'] += 1
                stats['problematic_books'].append({
                    'file': json_file.name,
                    'title': title,
                    'issue': 'no chapters detected'
                })
            
            stats['sentence_counts'].append(sentence_count)
            stats['word_counts'].append(word_count)
            
        except Exception as e:
            print(f"Error reading {json_file.name}: {e}")
    
    # Generate report
    print("\n" + "=" * 70)
    print("GUTENBERG JSON CONVERSION SUMMARY REPORT")
    print("=" * 70)
    
    print(f"\nTotal files converted: {stats['total_files']}")
    print(f"Books with chapters: {stats['books_with_chapters']}")
    print(f"Books without chapters: {stats['books_without_chapters']}")
    
    if stats['chapter_counts']:
        print(f"\nChapter Statistics:")
        print(f"  Total chapters: {sum(stats['chapter_counts']):,}")
        print(f"  Average per book: {statistics.mean(stats['chapter_counts']):.1f}")
        print(f"  Median: {statistics.median(stats['chapter_counts'])}")
        print(f"  Range: {min(stats['chapter_counts'])} - {max(stats['chapter_counts'])}")
    
    if stats['sentence_counts']:
        print(f"\nSentence Statistics:")
        print(f"  Total sentences: {sum(stats['sentence_counts']):,}")
        print(f"  Average per book: {statistics.mean(stats['sentence_counts']):.0f}")
    
    if stats['word_counts']:
        print(f"\nWord Statistics:")
        print(f"  Total words: {sum(stats['word_counts']):,}")
        print(f"  Average per book: {statistics.mean(stats['word_counts']):,.0f}")
        
        # Top 10 longest books
        print(f"\nTop 10 Longest Books (by word count):")
        sorted_by_words = sorted(
            [(title, wc) for (_, title, _), wc in zip(stats['titles'], stats['word_counts'])],
            key=lambda x: x[1],
            reverse=True
        )
        for i, (title, word_count) in enumerate(sorted_by_words[:10], 1):
            print(f"  {i}. {title[:50]:<50} {word_count:>8,} words")
    
    # Books without chapters
    if stats['problematic_books']:
        print(f"\nBooks without detected chapters ({len(stats['problematic_books'])}):")
        for book in stats['problematic_books'][:10]:
            print(f"  - {book['title'][:60]}")
        if len(stats['problematic_books']) > 10:
            print(f"  ... and {len(stats['problematic_books']) - 10} more")
    
    # Save detailed report
    report_file = json_path.parent / "conversion_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    return stats


def main():
    """Process all Gutenberg books to JSON and generate summary."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Process Gutenberg books to JSON format"
    )
    parser.add_argument(
        "--input", 
        default="book_texts",
        help="Input directory containing text files"
    )
    parser.add_argument(
        "--output",
        default="book_json",
        help="Output directory for JSON files"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of books to process"
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Skip summary report generation"
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only generate summary report (skip processing)"
    )
    
    args = parser.parse_args()
    
    if args.summary_only:
        # Just generate summary
        print("Generating summary report...")
        generate_summary_report(args.output)
        return
    
    print("=" * 70)
    print("GUTENBERG BOOKS TO JSON CONVERSION")
    print("=" * 70)
    print(f"Input directory: {args.input}")
    print(f"Output directory: {args.output}")
    if args.limit:
        print(f"Processing limit: {args.limit} books")
    print("=" * 70)
    
    # Start timer
    start_time = time.time()
    
    # Process all books
    stats = process_all_books(
        input_dir=args.input,
        output_dir=args.output,
        limit=args.limit,
        generate_summary=not args.no_summary
    )
    
    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    
    # Print final summary
    print("\n" + "=" * 70)
    print("CONVERSION COMPLETE")
    print("=" * 70)
    print(f"Time elapsed: {elapsed_time:.1f} seconds")
    if stats['total'] > 0:
        print(f"Average time per book: {elapsed_time/stats['total']:.1f} seconds")
    
    if stats['successful'] > 0:
        print(f"\nAverage chapters per book: {stats['total_chapters']/stats['successful']:.1f}")
        print(f"Average sentences per book: {stats['total_sentences']/stats['successful']:.0f}")
        print(f"Average words per book: {stats['total_words']/stats['successful']:.0f}")


if __name__ == "__main__":
    main()