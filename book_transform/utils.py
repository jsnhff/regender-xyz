#!/usr/bin/env python3
"""
Utility functions for book transformation.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
import functools

from openai import OpenAIError


class ReGenderError(Exception):
    """Base exception class for regender-xyz errors."""
    pass


class APIError(ReGenderError):
    """Exception raised for API-related errors."""
    pass


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