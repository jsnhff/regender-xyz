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

from typing import Dict, Any, Optional
from openai import OpenAIError

# Progress indicators
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'


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


def transform_with_characters(
    book_data: Dict[str, Any],
    character_file: str,
    transform_type: str = 'comprehensive',
    model: str = 'gpt-4o-mini',
    provider: Optional[str] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Transform a book using pre-analyzed character data.
    
    Args:
        book_data: The book data to transform
        character_file: Path to JSON file containing character analysis
        transform_type: Type of transformation to apply
        model: Model to use for transformation
        provider: LLM provider to use
        verbose: Whether to print progress
    
    Returns:
        Transformed book data with metadata about character source
    """
    from .transform import BookTransformer
    from book_characters.context import create_character_context
    
    if not Path(character_file).exists():
        raise FileNotFoundError(f"Character file not found: {character_file}")
    
    # Load character data
    with open(character_file, 'r') as f:
        character_data = json.load(f)
    
    # Extract characters (handle different formats)
    if 'characters' in character_data:
        characters = character_data['characters']
        context = character_data.get('context', '')
    else:
        # Assume the whole file is the character dict
        characters = character_data
        context = create_character_context(characters)
    
    if verbose:
        print(f"✅ Using pre-analyzed characters from: {character_file}")
        print(f"  Loaded {len(characters)} characters")
        
        # Show summary
        male_count = sum(1 for c in characters.values() if c.get('gender') == 'male')
        female_count = sum(1 for c in characters.values() if c.get('gender') == 'female')
        print(f"  Gender distribution: {male_count} male, {female_count} female")
    
    # Create transformer
    transformer = BookTransformer(provider=provider, model=model)
    
    # Directly set the characters and context on the transformer
    # This avoids calling analyze_book_characters
    transformed_data = book_data.copy()
    transformed_data['metadata'] = book_data.get('metadata', {}).copy()
    transformed_data['chapters'] = []
    
    # Track all changes
    all_changes = []
    
    # Get optimal chunk size for the model
    from .chunking.model_configs import calculate_optimal_chunk_size
    optimal_chunk_size = calculate_optimal_chunk_size(model)
    
    if verbose:
        print(f"\n{CYAN}Transforming {len(book_data['chapters'])} chapters...{RESET}")
    
    # Transform each chapter
    for i, chapter in enumerate(book_data['chapters']):
        chapter_num = i + 1
        if verbose:
            print(f"\n{BOLD}Chapter {chapter_num}/{len(book_data['chapters'])}{RESET}")
            print(f"    Using chunk size: {optimal_chunk_size} sentences (model: {model})")
        
        # Extract sentences from chapter
        sentences = []
        for para in chapter.get('paragraphs', []):
            para_sentences = para.get('sentences', [])
            # Ensure we have strings, not nested lists
            for sent in para_sentences:
                if isinstance(sent, str):
                    sentences.append(sent)
                elif isinstance(sent, list):
                    # Flatten if nested
                    sentences.extend(s for s in sent if isinstance(s, str))
        
        if not sentences:
            transformed_data['chapters'].append(chapter.copy())
            continue
        
        # Transform the chapter
        from .llm_transform import transform_gender_with_context
        from .chunking import smart_chunk_sentences
        
        if verbose:
            print(f"  Processing {chapter.get('title', '')} ({len(sentences)} sentences)...")
        
        # Smart chunking - create simple chunks
        chunks = []
        for i in range(0, len(sentences), optimal_chunk_size):
            chunk_sentences = sentences[i:i + optimal_chunk_size]
            # Estimate tokens
            from .chunking import estimate_tokens
            # Join sentences for token estimation
            chunk_text = ' '.join(chunk_sentences)
            token_estimate = estimate_tokens(chunk_text)
            chunks.append({
                'sentences': chunk_sentences,
                'token_estimate': token_estimate
            })
        
        # Transform each chunk
        transformed_sentences = []
        chapter_changes = []
        
        for chunk_idx, chunk_data in enumerate(chunks):
            chunk_sentences = chunk_data['sentences']
            token_estimate = chunk_data['token_estimate']
            if verbose:
                print(f"    Chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk_sentences)} sentences, ~{token_estimate} tokens)", end='')
            
            # Transform the chunk using numbered sentences approach
            actual_transform_type = transform_type
            
            # Use the numbered sentence approach from transform.py
            from .transform import transform_sentences_chunk
            
            # Transform the sentences
            transformed_sents, changes = transform_sentences_chunk(
                chunk_sentences,
                actual_transform_type,
                context,
                model,
                provider
            )
            
            # Add sentence indices to changes for this chunk
            for change in changes:
                change['sentence_index'] = change.get('sentence_index', 0) + len(transformed_sentences)
            
            transformed_sentences.extend(transformed_sents)
            chapter_changes.extend(changes)
            
            if verbose:
                print(f" - {len(changes)} changes")
        
        # Reconstruct chapter with transformed sentences
        transformed_chapter = chapter.copy()
        transformed_chapter['paragraphs'] = []
        
        # Reconstruct paragraphs
        sent_idx = 0
        for para in chapter.get('paragraphs', []):
            para_sentences = []
            for _ in range(len(para.get('sentences', []))):
                if sent_idx < len(transformed_sentences):
                    para_sentences.append(transformed_sentences[sent_idx])
                    sent_idx += 1
            
            if para_sentences:
                transformed_chapter['paragraphs'].append({
                    'sentences': para_sentences
                })
        
        transformed_data['chapters'].append(transformed_chapter)
        
        # Add chapter info to changes
        for change in chapter_changes:
            change['chapter'] = chapter_num
            change['chapter_title'] = chapter.get('title', '')
        
        all_changes.extend(chapter_changes)
    
    # Add metadata
    transformed_data['metadata']['character_source'] = character_file
    transformed_data['metadata']['character_analysis'] = 'pre-loaded'
    transformed_data['metadata']['transformation'] = {
        'type': transform_type,
        'model': model,
        'provider': provider,
        'timestamp': datetime.now().isoformat(),
        'total_changes': len(all_changes)
    }
    
    # Add character analysis results
    transformed_data['character_analysis'] = characters
    transformed_data['changes'] = all_changes
    
    return transformed_data