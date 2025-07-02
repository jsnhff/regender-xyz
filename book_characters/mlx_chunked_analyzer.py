"""Chunked character analysis for MLX models with large context windows."""

import json
from typing import Dict, Any, List, Optional, Tuple
from api_client import UnifiedLLMClient
from .prompts import get_character_analysis_prompt


def analyze_book_characters_chunked(
    book_data: Dict[str, Any],
    model: str = "mistral-small",
    provider: str = "mlx",
    chunk_size: int = 50000,
    overlap: int = 2000,
    verbose: bool = True
) -> Tuple[Dict[str, Any], str]:
    """
    Analyze characters in a book using chunked processing for MLX models.
    
    This is designed for large models that may run out of memory on limited systems.
    
    Args:
        book_data: Book JSON data
        model: Model name
        provider: Provider (should be 'mlx')
        chunk_size: Characters per chunk (default 50k for 64GB systems)
        overlap: Overlap between chunks
        verbose: Print progress
    
    Returns:
        Tuple of (characters dict, character context string)
    """
    if verbose:
        print(f"Analyzing characters with chunked MLX processing...")
        print(f"  Chunk size: {chunk_size} chars (~{chunk_size//4} tokens)")
        print(f"  Overlap: {overlap} chars")
    
    # Extract full text
    all_text = extract_book_text(book_data)
    total_length = len(all_text)
    
    if verbose:
        print(f"  Total text: {total_length} characters")
    
    # Create chunks
    chunks = []
    pos = 0
    while pos < total_length:
        chunk_end = min(pos + chunk_size, total_length)
        chunk = all_text[pos:chunk_end]
        chunks.append(chunk)
        pos += chunk_size - overlap
    
    if verbose:
        print(f"  Created {len(chunks)} chunks for analysis")
    
    # Initialize client once
    client = UnifiedLLMClient(provider=provider)
    all_characters = {}
    
    # Process each chunk
    for i, chunk_text in enumerate(chunks):
        if verbose:
            print(f"\n  Processing chunk {i+1}/{len(chunks)}...")
        
        # Create context from previously found characters
        prev_context = create_character_summary(all_characters) if all_characters else ""
        
        # Analyze chunk
        chunk_chars = analyze_single_chunk(
            chunk_text, 
            model, 
            client,
            chunk_num=i+1,
            total_chunks=len(chunks),
            previous_context=prev_context,
            verbose=verbose
        )
        
        # Merge results
        all_characters = merge_character_data(all_characters, chunk_chars)
        
        if verbose:
            print(f"    Found {len(chunk_chars)} characters in chunk")
            print(f"    Total unique characters: {len(all_characters)}")
    
    # Create character context
    context = create_character_context(all_characters)
    
    if verbose:
        print(f"\n✅ Analysis complete! Found {len(all_characters)} unique characters")
    
    return all_characters, context


def extract_book_text(book_data: Dict[str, Any]) -> str:
    """Extract all text from book data."""
    text_parts = []
    
    for chapter in book_data.get('chapters', []):
        # Add chapter title
        text_parts.append(f"\n\nCHAPTER: {chapter.get('title', 'Unknown')}\n")
        
        # Handle both paragraph and flat sentence structures
        if 'paragraphs' in chapter:
            for paragraph in chapter['paragraphs']:
                para_text = ' '.join(paragraph.get('sentences', []))
                text_parts.append(para_text)
        else:
            for sentence in chapter.get('sentences', []):
                text_parts.append(sentence)
    
    return '\n'.join(text_parts)


def analyze_single_chunk(
    chunk_text: str,
    model: str,
    client: UnifiedLLMClient,
    chunk_num: int,
    total_chunks: int,
    previous_context: str = "",
    verbose: bool = True
) -> Dict[str, Any]:
    """Analyze a single chunk of text."""
    # Get prompts
    system_prompt, base_user_prompt = get_character_analysis_prompt(chunk_text, model, "mlx")
    
    # Add chunk context to prompt
    chunk_info = f"\n[Analyzing chunk {chunk_num} of {total_chunks}]"
    if previous_context:
        chunk_info += f"\n\nPreviously identified characters:\n{previous_context}\n"
    
    user_prompt = chunk_info + "\n" + base_user_prompt
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = client.complete(
            messages=messages,
            model=model,
            temperature=0.0
        )
        
        # Parse response
        result_text = response.content.strip()
        
        # Extract JSON
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = result_text[json_start:json_end]
            data = json.loads(json_text)
            return data.get('characters', {})
        else:
            if verbose:
                print(f"    Warning: No valid JSON found in chunk {chunk_num}")
            return {}
            
    except Exception as e:
        if verbose:
            print(f"    Error in chunk {chunk_num}: {e}")
        return {}


def merge_character_data(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Merge new character data into existing data."""
    for char_name, char_info in new.items():
        if char_name in existing:
            # Merge information
            current = existing[char_name]
            
            # Update gender if previously unknown
            if current.get('gender') == 'unknown' and char_info.get('gender') != 'unknown':
                current['gender'] = char_info['gender']
            
            # Merge name variants
            current_variants = set(current.get('name_variants', []))
            new_variants = set(char_info.get('name_variants', []))
            current['name_variants'] = list(current_variants | new_variants)
            
            # Update role if more detailed
            if len(char_info.get('role', '')) > len(current.get('role', '')):
                current['role'] = char_info['role']
        else:
            # New character
            existing[char_name] = char_info
    
    return existing


def create_character_summary(characters: Dict[str, Any], max_chars: int = 20) -> str:
    """Create a summary of characters for context."""
    lines = []
    
    # Sort by number of variants (proxy for importance)
    sorted_chars = sorted(
        characters.items(), 
        key=lambda x: len(x[1].get('name_variants', [])), 
        reverse=True
    )
    
    for name, info in sorted_chars[:max_chars]:
        gender = info.get('gender', 'unknown')
        role = info.get('role', '')[:50]
        lines.append(f"- {name} ({gender}): {role}")
    
    return '\n'.join(lines)


def create_character_context(characters: Dict[str, Any]) -> str:
    """Create character context for transformation."""
    lines = ["Known characters:"]
    
    for name, info in characters.items():
        gender = info.get('gender', 'unknown')
        lines.append(f"- {name}: {gender}")
    
    return '\n'.join(lines)