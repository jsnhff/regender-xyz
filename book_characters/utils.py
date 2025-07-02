"""Utility functions for character analysis."""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json


def transform_with_characters(book_data: Dict[str, Any],
                            character_file: str,
                            transform_type: str = "comprehensive",
                            model: Optional[str] = None,
                            provider: Optional[str] = None,
                            verbose: bool = True) -> Dict[str, Any]:
    """Transform a book using pre-loaded character data.
    
    This function allows using pre-analyzed character data instead of
    re-analyzing the book, which saves time and API calls.
    
    Args:
        book_data: The book data to transform
        character_file: Path to the character analysis file
        transform_type: Type of transformation
        model: Model to use for transformation
        provider: Provider to use
        verbose: Whether to print progress
        
    Returns:
        Transformed book data
    """
    from .loader import load_character_file
    from .context import create_character_context
    from book_transform.transform import transform_book
    from unittest.mock import patch
    
    # Load character data
    characters = load_character_file(character_file)
    character_context = create_character_context(characters)
    
    if verbose:
        print(f"Loaded {len(characters)} characters from {character_file}")
        if characters:
            print(f"Main characters: {', '.join(list(characters.keys())[:5])}")
    
    # Mock the character analysis function to return our pre-loaded data
    def mock_analyze_book_characters(*args, **kwargs):
        return characters, character_context
    
    # Transform the book with our character data
    with patch('book_transform.transform.analyze_book_characters', mock_analyze_book_characters):
        return transform_book(
            book_data,
            transform_type=transform_type,
            model=model,
            provider=provider,
            verbose=verbose
        )


def estimate_character_analysis_cost(book_data: Dict[str, Any],
                                   model: str = "gpt-4o-mini",
                                   provider: str = "openai") -> Dict[str, Any]:
    """Estimate the cost of character analysis for a book.
    
    Args:
        book_data: The book data
        model: Model to use
        provider: Provider to use
        
    Returns:
        Dictionary with cost estimates
    """
    from .analyzer import get_full_text_from_json
    from book_transform.model_config_loader import get_verified_model_config
    
    # Get text length
    full_text = get_full_text_from_json(book_data)
    text_length = len(full_text)
    
    # Get model config
    config = get_verified_model_config(model, provider)
    if not config:
        return {
            "error": "Unknown model configuration",
            "model": model,
            "provider": provider
        }
    
    # Estimate tokens (roughly 4 chars per token)
    estimated_tokens = text_length // 4
    
    # Calculate chunks needed
    max_tokens = config.chunking.get('max_chunk_tokens', 4000)
    chunks_needed = (estimated_tokens + max_tokens - 1) // max_tokens
    
    # Cost estimates (these are rough - actual costs vary)
    cost_per_1k_tokens = {
        "gpt-4o-mini": 0.00015,  # $0.15 per 1M tokens
        "gpt-4o": 0.0025,        # $2.50 per 1M tokens
        "grok-beta": 0.001,      # Rough estimate
        "grok-3-mini-fast": 0.0005,  # Rough estimate
    }
    
    cost_rate = cost_per_1k_tokens.get(model, 0.001)
    estimated_cost = (estimated_tokens / 1000) * cost_rate
    
    return {
        "book_title": book_data.get('title', 'Unknown'),
        "text_length": text_length,
        "estimated_tokens": estimated_tokens,
        "chunks_needed": chunks_needed,
        "model": model,
        "provider": provider,
        "estimated_cost_usd": round(estimated_cost, 4),
        "notes": "Actual costs may vary based on response length and retries"
    }


def get_character_stats(characters: Dict[str, Any]) -> Dict[str, Any]:
    """Get statistics about the character data.
    
    Args:
        characters: Character data
        
    Returns:
        Dictionary with statistics
    """
    if not characters:
        return {
            "total_characters": 0,
            "male_characters": 0,
            "female_characters": 0,
            "unknown_gender": 0,
            "characters_with_variants": 0,
            "total_mentions": 0
        }
    
    stats = {
        "total_characters": len(characters),
        "male_characters": 0,
        "female_characters": 0,
        "unknown_gender": 0,
        "characters_with_variants": 0,
        "total_mentions": 0,
        "avg_mentions_per_character": 0,
        "most_mentioned_character": None,
        "least_mentioned_character": None
    }
    
    mention_counts = []
    
    for name, info in characters.items():
        # Gender stats
        gender = info.get('gender', 'unknown')
        if gender == 'male':
            stats['male_characters'] += 1
        elif gender == 'female':
            stats['female_characters'] += 1
        else:
            stats['unknown_gender'] += 1
        
        # Variant stats
        if info.get('name_variants'):
            stats['characters_with_variants'] += 1
        
        # Mention stats
        mentions = len(info.get('mentions', [])) or info.get('mentions', 0)
        stats['total_mentions'] += mentions
        mention_counts.append((name, mentions))
    
    # Calculate averages and extremes
    if mention_counts:
        stats['avg_mentions_per_character'] = round(
            stats['total_mentions'] / len(characters), 2
        )
        
        mention_counts.sort(key=lambda x: x[1], reverse=True)
        stats['most_mentioned_character'] = {
            "name": mention_counts[0][0],
            "mentions": mention_counts[0][1]
        }
        stats['least_mentioned_character'] = {
            "name": mention_counts[-1][0],
            "mentions": mention_counts[-1][1]
        }
    
    return stats


def filter_characters_by_mentions(characters: Dict[str, Any],
                                min_mentions: int = 5) -> Dict[str, Any]:
    """Filter characters by minimum number of mentions.
    
    Args:
        characters: Character data
        min_mentions: Minimum mentions required
        
    Returns:
        Filtered character dictionary
    """
    filtered = {}
    
    for name, info in characters.items():
        mentions = len(info.get('mentions', [])) or info.get('mentions', 0)
        if mentions >= min_mentions:
            filtered[name] = info
    
    return filtered