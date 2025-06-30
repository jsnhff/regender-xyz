#!/usr/bin/env python3
"""
Generate a summary report of the JSON conversion.
"""

import json
from pathlib import Path
from collections import Counter
import statistics


def generate_summary_report(json_dir: str = "gutenberg_json"):
    """Generate a summary report of all converted books."""
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
    
    print(f"\nSentence Statistics:")
    print(f"  Total sentences: {sum(stats['sentence_counts']):,}")
    print(f"  Average per book: {statistics.mean(stats['sentence_counts']):.0f}")
    
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
    report_file = "conversion_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("CONVERSION SUCCESS")
    print("=" * 70)
    print(f"✓ {stats['total_files']} books converted to clean JSON format")
    print(f"✓ {sum(stats['word_counts']):,} total words ready for processing")
    print(f"✓ Average book length: {statistics.mean(stats['word_counts']):,.0f} words")
    print(f"✓ All files saved to: {json_path.absolute()}/")


if __name__ == "__main__":
    generate_summary_report()