"""Utility to recreate formatted text from paragraph-aware JSON books."""

import json
from typing import Dict, Any
from pathlib import Path


def recreate_text_from_json(json_path: str, output_path: str = None) -> str:
    """Recreate formatted text from paragraph-aware JSON book.
    
    Args:
        json_path: Path to JSON book file
        output_path: Optional path to save recreated text
        
    Returns:
        The recreated text as a string
    """
    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        book_data = json.load(f)
    
    # Build text
    text_parts = []
    
    # Add metadata header if available
    metadata = book_data.get('metadata', {})
    if metadata.get('title') != 'Unknown':
        text_parts.append(f"Title: {metadata.get('title', 'Unknown')}")
    if metadata.get('author') != 'Unknown':
        text_parts.append(f"Author: {metadata.get('author', 'Unknown')}")
    if text_parts:
        text_parts.append('')  # Empty line after metadata
    
    # Process chapters
    for chapter in book_data.get('chapters', []):
        # Add chapter header
        chapter_header = []
        if chapter.get('number'):
            chapter_header.append(f"Chapter {chapter['number']}")
        if chapter.get('title'):
            if chapter_header:
                chapter_header.append(f": {chapter['title']}")
            else:
                chapter_header.append(chapter['title'])
        
        if chapter_header:
            text_parts.append(''.join(chapter_header))
            text_parts.append('')  # Empty line after chapter header
        
        # Process paragraphs
        for paragraph in chapter['paragraphs']:
            # Join sentences in paragraph
            para_text = ' '.join(paragraph.get('sentences', []))
            if para_text:  # Only add non-empty paragraphs
                text_parts.append(para_text)
                text_parts.append('')  # Empty line between paragraphs
        
        # Extra line between chapters
        text_parts.append('')
    
    # Join all parts
    recreated_text = '\n'.join(text_parts)
    
    # Clean up excessive empty lines
    import re
    recreated_text = re.sub(r'\n{3,}', '\n\n', recreated_text)
    recreated_text = recreated_text.strip()
    
    # Save if output path provided
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(recreated_text)
        print(f"Recreated text saved to: {output_path}")
    
    return recreated_text


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python recreate_text.py <json_file> [output_file]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    recreate_text_from_json(json_file, output_file)