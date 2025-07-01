"""Text formatter for recreating text from JSON book format."""

import json
from typing import Optional
from pathlib import Path


def recreate_text_from_json(json_file: str, output_file: Optional[str] = None, 
                           verbose: bool = True) -> str:
    """
    Recreate the original text from a clean JSON file.
    
    Args:
        json_file: Path to the JSON file
        output_file: Optional path to save the recreated text
        verbose: Whether to print progress messages
        
    Returns:
        The recreated text as a string
    """
    # Load JSON data
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if verbose:
        print(f"Recreating text from: {json_file}")
    
    parts = []
    
    # Add title if available
    if data.get('metadata', {}).get('title'):
        parts.append(data['metadata']['title'])
        parts.append("")  # blank line
    
    # Add author if available
    if data.get('metadata', {}).get('author'):
        parts.append(f"by {data['metadata']['author']}")
        parts.append("")  # blank line
    
    # Process chapters
    for chapter in data.get('chapters', []):
        # Add chapter title
        if chapter.get('title'):
            parts.append(chapter['title'])
            parts.append("")  # blank line after title
        
        # Handle both old (flat sentences) and new (paragraphs) structures
        if 'paragraphs' in chapter:
            # New structure with paragraphs
            paragraph_texts = []
            for paragraph in chapter['paragraphs']:
                para_text = ' '.join(paragraph.get('sentences', []))
                if para_text:  # Only add non-empty paragraphs
                    paragraph_texts.append(para_text)
            chapter_text = '\n\n'.join(paragraph_texts)
        elif 'sentences' in chapter:
            # Old structure with flat sentences
            chapter_text = ' '.join(chapter['sentences'])
            # Restore paragraph breaks where we have \n\n in sentences
            chapter_text = chapter_text.replace('\\n\\n', '\n\n')
        else:
            chapter_text = ""
        
        if chapter_text:
            parts.append(chapter_text)
    
    recreated_text = '\n'.join(parts)
    
    # Save if requested
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(recreated_text)
        if verbose:
            print(f"✓ Recreated text saved to: {output_file}")
    
    return recreated_text


def format_book_text(book_data: dict, include_metadata: bool = True) -> str:
    """
    Format book data as readable text.
    
    Args:
        book_data: Dictionary containing book data
        include_metadata: Whether to include title/author metadata
        
    Returns:
        Formatted text string
    """
    parts = []
    
    if include_metadata:
        # Add title if available
        if book_data.get('metadata', {}).get('title'):
            parts.append(book_data['metadata']['title'])
            parts.append("")  # blank line
        
        # Add author if available
        if book_data.get('metadata', {}).get('author'):
            parts.append(f"by {book_data['metadata']['author']}")
            parts.append("")  # blank line
    
    # Process chapters
    for chapter in book_data.get('chapters', []):
        # Add chapter title
        if chapter.get('title'):
            parts.append(chapter['title'])
            parts.append("")  # blank line after title
        
        # Handle both old (flat sentences) and new (paragraphs) structures
        if 'paragraphs' in chapter:
            # New structure with paragraphs
            paragraph_texts = []
            for paragraph in chapter['paragraphs']:
                para_text = ' '.join(paragraph.get('sentences', []))
                paragraph_texts.append(para_text)
            chapter_text = '\n\n'.join(paragraph_texts)
        elif 'sentences' in chapter:
            # Old structure with flat sentences
            chapter_text = ' '.join(chapter['sentences'])
            # Restore paragraph breaks
            chapter_text = chapter_text.replace('\\n\\n', '\n\n')
        else:
            chapter_text = ""
        
        parts.append(chapter_text)
        parts.append("")  # blank line between chapters
    
    return '\n'.join(parts).strip()