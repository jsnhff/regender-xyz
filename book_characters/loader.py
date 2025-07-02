"""Load pre-analyzed character data from files."""

import json
from pathlib import Path
from typing import Dict, Any, Optional


def load_character_file(file_path: str) -> Dict[str, Any]:
    """Load character data from a JSON file.
    
    Args:
        file_path: Path to the character JSON file
        
    Returns:
        Dictionary of character data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Character file not found: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Validate the structure
    if not isinstance(data, dict):
        raise ValueError("Character file must contain a JSON object")
    
    # If the data has a 'characters' key, use that
    if 'characters' in data:
        return data['characters']
    
    # Otherwise assume the whole file is the character dict
    return data


def validate_character_data(characters: Dict[str, Any]) -> bool:
    """Validate that character data has the expected structure.
    
    Args:
        characters: Character data to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(characters, dict):
        return False
    
    for name, info in characters.items():
        if not isinstance(info, dict):
            return False
        
        # Check required fields
        if 'name' not in info or 'gender' not in info:
            return False
        
        # Check gender is valid
        if info['gender'] not in ['male', 'female', 'unknown']:
            return False
    
    return True


def find_character_file(book_path: str) -> Optional[str]:
    """Find a character file associated with a book.
    
    Looks for files with _characters.json suffix in the same directory.
    
    Args:
        book_path: Path to the book JSON file
        
    Returns:
        Path to character file if found, None otherwise
    """
    book_path = Path(book_path)
    book_dir = book_path.parent
    book_stem = book_path.stem
    
    # Try different naming patterns
    patterns = [
        f"{book_stem}_characters.json",
        f"{book_stem}_chars.json",
        f"{book_stem}.characters.json"
    ]
    
    for pattern in patterns:
        char_path = book_dir / pattern
        if char_path.exists():
            return str(char_path)
    
    return None


def merge_character_data(primary: Dict[str, Any], 
                        secondary: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two character dictionaries, preferring primary data.
    
    Args:
        primary: Primary character data (takes precedence)
        secondary: Secondary character data
        
    Returns:
        Merged character dictionary
    """
    merged = dict(secondary)  # Start with secondary
    
    for name, info in primary.items():
        if name in merged:
            # Merge the info, preferring primary
            merged_info = dict(merged[name])
            merged_info.update(info)
            merged[name] = merged_info
        else:
            merged[name] = info
    
    return merged