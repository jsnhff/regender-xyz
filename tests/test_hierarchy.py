#!/usr/bin/env python3
"""Test the hierarchy builder."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parsers.gutenberg import GutenbergParser
from src.parsers.detector import FormatDetector
from src.parsers.hierarchy import HierarchyBuilder, SectionType


def test_book(book_path: str):
    """Test hierarchy building on a book."""
    book_name = os.path.basename(book_path)
    print(f"\n{'='*60}")
    print(f"Testing: {book_name}")
    print('='*60)
    
    # Read and clean the book
    with open(book_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    cleaner = GutenbergParser()
    cleaned_text, metadata = cleaner.clean(raw_text)
    
    # Detect format
    detector = FormatDetector()
    detection = detector.detect(cleaned_text)
    print(f"Format: {detection.format.value} ({detection.confidence:.0f}%)")
    
    # Build hierarchy
    builder = HierarchyBuilder()
    lines = cleaned_text.split('\n')
    hierarchy = builder.build_hierarchy(lines, detection.format.value)
    
    # Show structure
    print("\nHierarchy Structure:")
    print_section(hierarchy, indent=0)
    
    # Convert to flat chapters
    chapters = hierarchy.to_flat_chapters()
    print(f"\nTotal chapters/sections: {len(chapters)}")
    
    # Show first few chapters
    print("\nFirst 5 chapters:")
    for i, chapter in enumerate(chapters[:5]):
        parent = chapter.get('parent', '')
        if parent:
            print(f"  {i+1}. [{parent}] {chapter['title']}")
        else:
            print(f"  {i+1}. {chapter['title']}")


def print_section(section, indent=0):
    """Print section hierarchy."""
    prefix = "  " * indent
    
    # Don't show root book node
    if section.type != SectionType.BOOK or indent > 0:
        title = section.get_full_title()
        content_lines = len(section.content)
        if section.subsections:
            print(f"{prefix}{title} ({len(section.subsections)} subsections, {content_lines} lines)")
        else:
            print(f"{prefix}{title} ({content_lines} lines)")
    
    # Print subsections
    for subsection in section.subsections[:10]:  # Limit to first 10
        print_section(subsection, indent + 1)
    
    if len(section.subsections) > 10:
        print(f"{prefix}  ... and {len(section.subsections) - 10} more")


def main():
    """Test with sample books."""
    # Get the base directory (parent of tests/)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    test_books = [
        os.path.join(base_dir, "books/texts/pg1184-The_Count_of_Monte_Cristo.txt"),  # Multi-part
        os.path.join(base_dir, "books/texts/pg11-Alice's_Adventures_in_Wonderland.txt"),  # Standard
    ]
    
    for book_path in test_books:
        if os.path.exists(book_path):
            test_book(book_path)
        else:
            print(f"Book not found: {book_path}")


if __name__ == "__main__":
    main()