"""Text formatter for recreating text from JSON book format."""

import json
from typing import Optional
from pathlib import Path


def normalize_unicode_to_ascii(text: str) -> str:
    """
    Convert common Unicode characters to ASCII equivalents.
    
    Args:
        text: Text containing Unicode characters
        
    Returns:
        Text with Unicode characters replaced by ASCII equivalents
    """
    # Common Unicode replacements
    replacements = {
        '\u2019': "'",  # Right single quotation mark
        '\u2018': "'",  # Left single quotation mark
        '\u201C': '"',  # Left double quotation mark
        '\u201D': '"',  # Right double quotation mark
        '\u2014': '--', # Em dash
        '\u2013': '-',  # En dash
        '\u2026': '...', # Ellipsis
        '\u00A0': ' ',  # Non-breaking space
        '\u2012': '-',  # Figure dash
        '\u2010': '-',  # Hyphen
        '\u2011': '-',  # Non-breaking hyphen
        '\u00E9': 'e',  # é (e with acute)
        '\u00E8': 'e',  # è (e with grave)
        '\u00E0': 'a',  # à (a with grave)
        '\u00E2': 'a',  # â (a with circumflex)
        '\u00F4': 'o',  # ô (o with circumflex)
        '\u00FB': 'u',  # û (u with circumflex)
        '\u00E7': 'c',  # ç (c with cedilla)
        '\u00FC': 'u',  # ü (u with umlaut)
        '\u00F6': 'o',  # ö (o with umlaut)
        '\u00E4': 'a',  # ä (a with umlaut)
    }
    
    result = text
    for unicode_char, ascii_char in replacements.items():
        result = result.replace(unicode_char, ascii_char)
    
    return result


def recreate_text_from_json(json_file: str, output_file: Optional[str] = None, 
                           verbose: bool = True, normalize_unicode: bool = True) -> str:
    """
    Recreate the original text from a clean JSON file.
    
    Args:
        json_file: Path to the JSON file
        output_file: Optional path to save the recreated text
        verbose: Whether to print progress messages
        normalize_unicode: Whether to convert Unicode characters to ASCII equivalents
        
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
    for i, chapter in enumerate(data.get('chapters', [])):
        # Add extra spacing before chapters (except the first one)
        if i > 0:
            parts.append("")  # Add extra blank line between chapters
        
        # Add chapter heading (number and/or title)
        chapter_heading = ""
        
        # Check for chapter number
        if chapter.get('number'):
            # Format based on type
            if chapter.get('type') == 'act':
                chapter_heading = f"ACT {chapter['number']}"
            elif chapter.get('type') == 'scene':
                chapter_heading = f"SCENE {chapter['number']}"
            else:
                chapter_heading = f"CHAPTER {chapter['number']}"
        
        # Add title if present
        if chapter.get('title'):
            if chapter_heading:
                chapter_heading += f": {chapter['title']}"
            else:
                chapter_heading = chapter['title']
        
        # Add the heading if we have one
        if chapter_heading:
            parts.append(chapter_heading)
            parts.append("")  # blank line after heading
        
        # Process paragraphs
        paragraph_texts = []
        for paragraph in chapter['paragraphs']:
            para_text = ' '.join(paragraph.get('sentences', []))
            if para_text:  # Only add non-empty paragraphs
                paragraph_texts.append(para_text)
        chapter_text = '\n\n'.join(paragraph_texts)
        
        if chapter_text:
            parts.append(chapter_text)
    
    recreated_text = '\n'.join(parts)
    
    # Normalize Unicode if requested
    if normalize_unicode:
        recreated_text = normalize_unicode_to_ascii(recreated_text)
    
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
    for i, chapter in enumerate(book_data.get('chapters', [])):
        # Add extra spacing before chapters (except the first one)
        if i > 0:
            parts.append("")  # Add extra blank line between chapters
        
        # Add chapter heading (number and/or title)
        chapter_heading = ""
        
        # Check for chapter number
        if chapter.get('number'):
            # Format based on type
            if chapter.get('type') == 'act':
                chapter_heading = f"ACT {chapter['number']}"
            elif chapter.get('type') == 'scene':
                chapter_heading = f"SCENE {chapter['number']}"
            else:
                chapter_heading = f"CHAPTER {chapter['number']}"
        
        # Add title if present
        if chapter.get('title'):
            if chapter_heading:
                chapter_heading += f": {chapter['title']}"
            else:
                chapter_heading = chapter['title']
        
        # Add the heading if we have one
        if chapter_heading:
            parts.append(chapter_heading)
            parts.append("")  # blank line after heading
        
        # Process paragraphs
        paragraph_texts = []
        for paragraph in chapter['paragraphs']:
            para_text = ' '.join(paragraph.get('sentences', []))
            paragraph_texts.append(para_text)
        chapter_text = '\n\n'.join(paragraph_texts)
        
        parts.append(chapter_text)
        parts.append("")  # blank line between chapters
    
    return '\n'.join(parts).strip()