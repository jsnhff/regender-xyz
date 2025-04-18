#!/usr/bin/env python3
"""
Utility functions for regender-xyz.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
import functools

from openai import OpenAI, OpenAIError


class ReGenderError(Exception):
    """Base exception class for regender-xyz errors."""
    pass


class APIError(ReGenderError):
    """Exception raised for API-related errors."""
    pass


class FileError(ReGenderError):
    """Exception raised for file-related errors."""
    pass


class ValidationError(ReGenderError):
    """Exception raised for validation errors."""
    pass


def validate_file_path(file_path: str) -> Path:
    """Validate that a file exists and is readable.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        Path object for the validated file
        
    Raises:
        FileError: If the file doesn't exist or isn't readable
    """
    path = Path(file_path)
    if not path.exists():
        raise FileError(f"File not found: {file_path}")
    if not path.is_file():
        raise FileError(f"Not a file: {file_path}")
    if not os.access(path, os.R_OK):
        raise FileError(f"File is not readable: {file_path}")
    return path


def load_text_file(file_path: str) -> str:
    """Load text from a file with proper error handling.
    
    Args:
        file_path: Path to the text file to load
        
    Returns:
        The text content of the file
        
    Raises:
        FileError: If the file can't be loaded
    """
    try:
        path = validate_file_path(file_path)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        raise FileError(f"File is not valid UTF-8 text: {file_path}")
    except Exception as e:
        raise FileError(f"Error loading file: {e}")


def save_text_file(content: str, file_path: str) -> None:
    """Save text to a file with proper error handling.
    
    Args:
        content: Text content to save
        file_path: Path to save the text to
        
    Raises:
        FileError: If the file can't be saved
    """
    try:
        # Create directory if it doesn't exist
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        raise FileError(f"Error saving file: {e}")


def save_json_file(data: Dict, file_path: str) -> None:
    """Save JSON data to a file with proper error handling.
    
    Args:
        data: JSON-serializable data to save
        file_path: Path to save the JSON to
        
    Raises:
        FileError: If the file can't be saved
    """
    try:
        # Create directory if it doesn't exist
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise FileError(f"Error saving JSON file: {e}")


def load_json_file(file_path: str) -> Dict:
    """Load JSON data from a file with proper error handling.
    
    Args:
        file_path: Path to the JSON file to load
        
    Returns:
        The parsed JSON data
        
    Raises:
        FileError: If the file can't be loaded or parsed
    """
    try:
        path = validate_file_path(file_path)
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise FileError(f"File is not valid JSON: {file_path}")
    except Exception as e:
        raise FileError(f"Error loading JSON file: {e}")


def get_openai_client() -> OpenAI:
    """Get an OpenAI client with proper error handling.
    
    Returns:
        OpenAI client instance
        
    Raises:
        APIError: If the API key is not set or invalid
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise APIError("OPENAI_API_KEY environment variable not set")
    
    try:
        return OpenAI(api_key=api_key)
    except Exception as e:
        raise APIError(f"Error initializing OpenAI client: {e}")


def cache_result(cache_dir: str = ".cache"):
    """Decorator to cache function results based on input parameters.
    
    Args:
        cache_dir: Directory to store cache files
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if cache is disabled via environment variable
            if os.environ.get('REGENDER_DISABLE_CACHE') == '1':
                # Skip cache and call the original function directly
                return func(*args, **kwargs)
            
            # Create cache directory if it doesn't exist
            cache_path = Path(cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)
            
            # Create a cache key based on function name and arguments
            cache_key = f"{func.__name__}_{args}_{kwargs}"
            cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = cache_path / f"{cache_hash}.json"
            
            # Check if cache file exists and is not too old (1 day)
            if cache_file.exists():
                try:
                    cache_data = json.loads(cache_file.read_text())
                    cache_time = datetime.fromisoformat(cache_data["timestamp"])
                    if (datetime.now() - cache_time).days < 1:
                        return cache_data["result"]
                except (json.JSONDecodeError, KeyError, ValueError):
                    # If cache is invalid, just continue and recalculate
                    pass
            
            # Call the original function
            result = func(*args, **kwargs)
            
            # Save result to cache
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "result": result
            }
            cache_file.write_text(json.dumps(cache_data))
            
            return result
        return wrapper
    return decorator


def normalize_text(text: str) -> str:
    """Ensure consistent line endings and no double spaces.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text
    """
    # Convert all line endings to \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Ensure single newline at start and no double spaces
    return '\n' + ' '.join(text.split())


def find_text_position(text: str, search_text: str) -> Optional[Dict]:
    """Find the position of text within a larger text.
    
    Args:
        text: The text to search in
        search_text: The text to search for
        
    Returns:
        Dictionary with position information or None if not found
    """
    pos = text.find(search_text)
    if pos >= 0:
        context_start = max(0, text.rfind('\n', 0, pos) + 1)
        context_end = text.find('\n', pos)
        if context_end == -1:
            context_end = len(text)
        return {
            'start': pos,
            'end': pos + len(search_text),
            'text': text[pos:pos + len(search_text)],
            'context': text[context_start:context_end]
        }
    return None


def safe_api_call(func):
    """Decorator to handle API calls safely with proper error handling.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OpenAIError as e:
            raise APIError(f"OpenAI API error: {e}")
        except Exception as e:
            raise APIError(f"Unexpected error during API call: {e}")
    return wrapper
