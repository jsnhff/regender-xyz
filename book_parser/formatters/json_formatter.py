"""JSON formatter for saving and loading book data."""

import json
from typing import Any, Dict, Optional
from pathlib import Path


def save_book_json(book_data: Dict[str, Any], output_file: str, 
                   pretty: bool = True, ensure_ascii: bool = False) -> None:
    """
    Save book data to JSON file.
    
    Args:
        book_data: Dictionary containing book data
        output_file: Path to output JSON file
        pretty: Whether to format JSON with indentation
        ensure_ascii: Whether to escape non-ASCII characters
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(book_data, f, indent=2, ensure_ascii=ensure_ascii)
        else:
            json.dump(book_data, f, ensure_ascii=ensure_ascii)


def load_book_json(json_file: str) -> Dict[str, Any]:
    """
    Load book data from JSON file.
    
    Args:
        json_file: Path to JSON file
        
    Returns:
        Dictionary containing book data
        
    Raises:
        FileNotFoundError: If JSON file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_book_json(book_data: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate book JSON structure.
    
    Args:
        book_data: Dictionary containing book data
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required top-level fields
    if 'metadata' not in book_data:
        errors.append("Missing 'metadata' field")
    
    if 'chapters' not in book_data:
        errors.append("Missing 'chapters' field")
    
    if 'statistics' not in book_data:
        errors.append("Missing 'statistics' field")
    
    # Validate metadata
    if 'metadata' in book_data:
        metadata = book_data['metadata']
        if not isinstance(metadata, dict):
            errors.append("'metadata' must be a dictionary")
    
    # Validate chapters
    if 'chapters' in book_data:
        chapters = book_data['chapters']
        if not isinstance(chapters, list):
            errors.append("'chapters' must be a list")
        else:
            for i, chapter in enumerate(chapters):
                if not isinstance(chapter, dict):
                    errors.append(f"Chapter {i} must be a dictionary")
                    continue
                
                # Check required chapter fields
                if 'number' not in chapter:
                    errors.append(f"Chapter {i} missing 'number' field")
                
                if 'title' not in chapter:
                    errors.append(f"Chapter {i} missing 'title' field")
                
                if 'sentences' not in chapter:
                    errors.append(f"Chapter {i} missing 'sentences' field")
                elif not isinstance(chapter['sentences'], list):
                    errors.append(f"Chapter {i} 'sentences' must be a list")
    
    # Validate statistics
    if 'statistics' in book_data:
        stats = book_data['statistics']
        if not isinstance(stats, dict):
            errors.append("'statistics' must be a dictionary")
        else:
            required_stats = ['total_chapters', 'total_sentences', 'total_words']
            for stat in required_stats:
                if stat not in stats:
                    errors.append(f"Missing statistic: {stat}")
    
    return len(errors) == 0, errors


def merge_book_metadata(book_data: Dict[str, Any], 
                       additional_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge additional metadata into book data.
    
    Args:
        book_data: Original book data
        additional_metadata: Additional metadata to merge
        
    Returns:
        Updated book data (modifies in place and returns)
    """
    if 'metadata' not in book_data:
        book_data['metadata'] = {}
    
    book_data['metadata'].update(additional_metadata)
    return book_data


def extract_book_summary(book_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a summary of book data without the full text.
    
    Args:
        book_data: Full book data
        
    Returns:
        Summary dictionary with metadata and statistics
    """
    summary = {
        'metadata': book_data.get('metadata', {}),
        'statistics': book_data.get('statistics', {}),
        'chapter_count': len(book_data.get('chapters', [])),
        'chapters': []
    }
    
    # Add chapter summaries (without sentences)
    for chapter in book_data.get('chapters', []):
        chapter_summary = {
            'number': chapter.get('number'),
            'title': chapter.get('title'),
            'sentence_count': len(chapter.get('sentences', [])),
            'word_count': chapter.get('word_count', 0)
        }
        summary['chapters'].append(chapter_summary)
    
    return summary