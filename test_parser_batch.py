#!/usr/bin/env python3
"""
Batch test the refined parser on all 100 Gutenberg books.
"""

import json
import time
from pathlib import Path
from collections import Counter, defaultdict
import statistics
from book_parser_v2 import parse_book, ParsedBook


def test_all_books(texts_dir: str = "gutenberg_texts", output_dir: str = "parsed_books"):
    """Test parser on all books and collect statistics."""
    texts_path = Path(texts_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Statistics
    stats = {
        'total_books': 0,
        'successful': 0,
        'failed': 0,
        'books_with_metadata': 0,
        'books_with_chapters': 0,
        'chapter_counts': [],
        'section_types': Counter(),
        'errors': []
    }
    
    # Process each book
    text_files = sorted(texts_path.glob("*.txt"))
    
    print(f"Testing parser on {len(text_files)} books...")
    print("-" * 60)
    
    for i, filepath in enumerate(text_files):
        print(f"[{i+1}/{len(text_files)}] {filepath.name}...", end=" ")
        
        try:
            # Parse the book
            book = parse_book(str(filepath))
            
            # Save parsed data
            output_file = output_path / f"{filepath.stem}_parsed.json"
            save_simple_json(book, str(output_file))
            
            # Collect statistics
            stats['successful'] += 1
            
            if book.metadata.get('title') or book.metadata.get('author'):
                stats['books_with_metadata'] += 1
            
            if book.chapters:
                stats['books_with_chapters'] += 1
                stats['chapter_counts'].append(len(book.chapters))
            
            for section in book.sections:
                stats['section_types'][section.type.value] += 1
            
            print(f"✓ {len(book.chapters)} chapters")
            
        except Exception as e:
            stats['failed'] += 1
            stats['errors'].append({
                'file': filepath.name,
                'error': str(e)
            })
            print(f"✗ ERROR: {str(e)[:50]}...")
        
        stats['total_books'] += 1
    
    # Calculate final statistics
    print("\n" + "=" * 60)
    print("PARSING RESULTS")
    print("=" * 60)
    
    print(f"\nTotal books: {stats['total_books']}")
    print(f"Successful: {stats['successful']} ({stats['successful']/stats['total_books']*100:.1f}%)")
    print(f"Failed: {stats['failed']}")
    
    print(f"\nBooks with metadata: {stats['books_with_metadata']}")
    print(f"Books with chapters: {stats['books_with_chapters']}")
    
    if stats['chapter_counts']:
        print(f"\nChapter statistics:")
        print(f"  Average: {statistics.mean(stats['chapter_counts']):.1f}")
        print(f"  Median: {statistics.median(stats['chapter_counts'])}")
        print(f"  Min: {min(stats['chapter_counts'])}")
        print(f"  Max: {max(stats['chapter_counts'])}")
    
    print(f"\nSection types found:")
    for section_type, count in stats['section_types'].most_common(10):
        print(f"  {section_type}: {count}")
    
    if stats['errors']:
        print(f"\nErrors ({len(stats['errors'])}):")
        for error in stats['errors'][:5]:
            print(f"  {error['file']}: {error['error']}")
    
    # Save statistics
    with open('parser_test_results.json', 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    
    print(f"\nResults saved to parser_test_results.json")


def save_simple_json(book: ParsedBook, output_file: str):
    """Save parsed book in a simple JSON format."""
    # Create simple structure
    data = {
        'metadata': book.metadata,
        'chapter_count': len(book.chapters),
        'section_count': len(book.sections),
        'chapters': []
    }
    
    # Add chapter summaries
    for ch in book.chapters[:10]:  # First 10 chapters
        data['chapters'].append({
            'number': ch.number,
            'title': ch.title,
            'word_count': len(ch.content.split()),
            'preview': ch.content[:200] + '...' if len(ch.content) > 200 else ch.content
        })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def analyze_failures():
    """Analyze books that failed to parse properly."""
    results_file = Path('parser_test_results.json')
    if not results_file.exists():
        print("No results file found. Run test_all_books first.")
        return
    
    with open(results_file) as f:
        stats = json.load(f)
    
    print("\nFAILURE ANALYSIS")
    print("=" * 60)
    
    # Books without chapters
    parsed_dir = Path('parsed_books')
    no_chapters = []
    
    for parsed_file in parsed_dir.glob("*_parsed.json"):
        with open(parsed_file) as f:
            data = json.load(f)
        
        if data['chapter_count'] == 0:
            no_chapters.append(parsed_file.stem.replace('_parsed', ''))
    
    if no_chapters:
        print(f"\nBooks without chapters ({len(no_chapters)}):")
        for book in no_chapters[:10]:
            print(f"  - {book}")
    
    # Common error patterns
    if stats.get('errors'):
        error_types = Counter()
        for error in stats['errors']:
            # Categorize error
            if 'encoding' in error['error'].lower():
                error_types['encoding'] += 1
            elif 'list index' in error['error'].lower():
                error_types['index'] += 1
            else:
                error_types['other'] += 1
        
        print(f"\nError types:")
        for error_type, count in error_types.items():
            print(f"  {error_type}: {count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test parser on all books")
    parser.add_argument("--analyze", action="store_true", help="Analyze failures")
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_failures()
    else:
        test_all_books()