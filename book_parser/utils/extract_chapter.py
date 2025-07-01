#!/usr/bin/env python3
"""
Extract specific chapters from a book JSON file for testing.

This utility is useful for:
- Testing transformations on smaller samples
- Debugging specific chapters
- Creating test datasets for local models with limited context
- Validating chapter parsing

Usage:
    python extract_chapter.py
"""

import json
import sys
from pathlib import Path

def extract_chapters(book_file, chapter_numbers=None, max_sentences=None):
    """Extract specific chapters from a book.
    
    Args:
        book_file: Path to book JSON file
        chapter_numbers: List of chapter numbers to extract (1-based), or None for all
        max_sentences: Max sentences per chapter to keep
    """
    with open(book_file, 'r') as f:
        book_data = json.load(f)
    
    # Create a subset
    subset = {
        "metadata": book_data.get("metadata", {}),
        "chapters": []
    }
    
    # Extract requested chapters
    for i, chapter in enumerate(book_data.get("chapters", [])):
        chapter_num = i + 1
        if chapter_numbers is None or chapter_num in chapter_numbers:
            chapter_copy = chapter.copy()
            
            # Limit sentences if requested
            if max_sentences and len(chapter_copy.get("sentences", [])) > max_sentences:
                chapter_copy["sentences"] = chapter_copy["sentences"][:max_sentences]
                chapter_copy["title"] = f"{chapter_copy.get('title', '')} (first {max_sentences} sentences)"
            
            subset["chapters"].append(chapter_copy)
    
    # Update statistics
    if "statistics" in book_data:
        subset["statistics"] = {
            "total_chapters": len(subset["chapters"]),
            "total_sentences": sum(len(ch.get("sentences", [])) for ch in subset["chapters"])
        }
    
    return subset

if __name__ == "__main__":
    # Extract chapter 1 of Moby Dick with first 10 sentences
    moby_subset = extract_chapters(
        "book_json/pg2701-Mo_clean.json", 
        chapter_numbers=[8],  # Chapter 8 is "Loomings" - the first real chapter
        max_sentences=10
    )
    
    # Save it
    output_file = "moby_dick_chapter1_sample.json"
    with open(output_file, 'w') as f:
        json.dump(moby_subset, f, indent=2)
    
    print(f"✓ Extracted chapter to {output_file}")
    print(f"  Chapters: {moby_subset['statistics']['total_chapters']}")
    print(f"  Sentences: {moby_subset['statistics']['total_sentences']}")
    
    # Also create a multi-chapter sample
    moby_subset_multi = extract_chapters(
        "book_json/pg2701-Mo_clean.json", 
        chapter_numbers=[8, 9, 10],  # First 3 real chapters
        max_sentences=20
    )
    
    output_file2 = "moby_dick_3chapters_sample.json"
    with open(output_file2, 'w') as f:
        json.dump(moby_subset_multi, f, indent=2)
    
    print(f"\n✓ Extracted 3 chapters to {output_file2}")
    print(f"  Chapters: {moby_subset_multi['statistics']['total_chapters']}")
    print(f"  Sentences: {moby_subset_multi['statistics']['total_sentences']}")