"""Chunked character analysis for API providers (OpenAI, Grok, etc.)."""

import json
from typing import Dict, Any, List, Tuple
from api_client import UnifiedLLMClient
from .prompts import get_character_analysis_prompt


def analyze_book_characters_chunked_api(
    book_data: Dict[str, Any],
    model: str,
    provider: str,
    max_tokens_per_chunk: int = 30000,
    verbose: bool = True
) -> Tuple[Dict[str, Any], str]:
    """
    Analyze characters in a book using chunked processing for API providers.
    
    This is for when a book is too large to fit in a single API call.
    
    Args:
        book_data: Book JSON data
        model: Model name
        provider: Provider name
        max_tokens_per_chunk: Maximum tokens per chunk
        verbose: Print progress
    
    Returns:
        Tuple of (characters dict, character context string)
    """
    if verbose:
        print(f"Analyzing characters with chunked API processing...")
        print(f"  Max tokens per chunk: {max_tokens_per_chunk}")
    
    # Extract full text
    all_text = extract_book_text(book_data)
    total_length = len(all_text)
    
    # Estimate tokens and create chunks
    # Rough estimate: 4 characters per token
    # For Grok with 131k context, we can be more aggressive
    if provider == 'grok' and max_tokens_per_chunk > 50000:
        # Grok can handle larger chunks - use 80% of limit
        max_chars_per_chunk = int(max_tokens_per_chunk * 4 * 0.8)
    else:
        max_chars_per_chunk = max_tokens_per_chunk * 4
    
    if verbose:
        print(f"  Total text: {total_length} characters (~{total_length // 4} tokens)")
        print(f"  Using chunks of ~{max_chars_per_chunk} characters")
    
    # Create chunks without overlap for API providers (they're fast enough)
    chunks = []
    pos = 0
    while pos < total_length:
        chunk_end = min(pos + max_chars_per_chunk, total_length)
        chunks.append(all_text[pos:chunk_end])
        pos = chunk_end
    
    if verbose:
        print(f"  Created {len(chunks)} chunks for analysis")
    
    # Initialize client once
    client = UnifiedLLMClient(provider=provider)
    all_characters = {}
    
    # Process each chunk
    for i, chunk_text in enumerate(chunks):
        if verbose:
            print(f"\n  Processing chunk {i+1}/{len(chunks)}...")
        
        # Create context from previously found characters (for consistency)
        prev_summary = create_character_summary(all_characters) if all_characters else ""
        
        # Analyze chunk
        chunk_chars = analyze_single_chunk_api(
            chunk_text, 
            model, 
            client,
            chunk_num=i+1,
            total_chunks=len(chunks),
            previous_summary=prev_summary,
            verbose=verbose
        )
        
        # Merge results carefully
        all_characters = merge_character_data_safe(all_characters, chunk_chars)
        
        if verbose:
            print(f"    Found {len(chunk_chars)} characters in chunk")
            print(f"    Total unique characters: {len(all_characters)}")
    
    # Create character context
    from .context import create_character_context
    context = create_character_context(all_characters)
    
    if verbose:
        print(f"\n✅ Analysis complete! Found {len(all_characters)} unique characters")
    
    return all_characters, context


def extract_book_text(book_data: Dict[str, Any]) -> str:
    """Extract all text from book data."""
    text_parts = []
    
    for chapter in book_data.get('chapters', []):
        # Add chapter title
        if chapter.get('title'):
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


def analyze_single_chunk_api(
    chunk_text: str,
    model: str,
    client: UnifiedLLMClient,
    chunk_num: int,
    total_chunks: int,
    previous_summary: str = "",
    verbose: bool = True
) -> Dict[str, Any]:
    """Analyze a single chunk of text."""
    # Get prompts
    system_prompt, base_user_prompt = get_character_analysis_prompt(chunk_text, model, client.provider)
    
    # Add chunk context to prompt
    chunk_info = f"\n[Analyzing chunk {chunk_num} of {total_chunks}]"
    if previous_summary:
        chunk_info += f"\n\nPreviously identified characters (for reference only - analyze this chunk independently):\n{previous_summary}\n"
    
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
        try:
            # Try direct parse first
            data = json.loads(result_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = result_text[json_start:json_end]
                data = json.loads(json_text)
            else:
                if verbose:
                    print(f"    Warning: No valid JSON found in chunk {chunk_num}")
                return {}
        
        return data.get('characters', {})
            
    except Exception as e:
        if verbose:
            print(f"    Error in chunk {chunk_num}: {e}")
        return {}


def merge_character_data_safe(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Safely merge new character data into existing data."""
    for char_name, char_info in new.items():
        if char_name in existing:
            # Character exists - only update if more information
            current = existing[char_name]
            
            # Update gender only if currently unknown
            if current.get('gender') == 'unknown' and char_info.get('gender') != 'unknown':
                current['gender'] = char_info['gender']
            
            # Update role if new one is longer/more detailed
            if len(char_info.get('role', '')) > len(current.get('role', '')):
                current['role'] = char_info['role']
            
            # Merge alternate names (but validate they make sense)
            if 'name_variants' in char_info:
                current_variants = set(current.get('name_variants', []))
                new_variants = set(char_info.get('name_variants', []))
                
                # Only add variants that seem related (share words)
                char_words = set(char_name.lower().split())
                for variant in new_variants:
                    variant_words = set(variant.lower().split())
                    if char_words & variant_words:  # Share at least one word
                        current_variants.add(variant)
                
                current['name_variants'] = list(current_variants)
        else:
            # New character - add directly
            existing[char_name] = char_info
    
    return existing


def create_character_summary(characters: Dict[str, Any], max_chars: int = 15) -> str:
    """Create a brief summary of characters for context."""
    lines = []
    
    # Just list character names and genders
    for i, (name, info) in enumerate(characters.items()):
        if i >= max_chars:
            lines.append(f"... and {len(characters) - max_chars} more")
            break
        gender = info.get('gender', 'unknown')
        lines.append(f"- {name} ({gender})")
    
    return '\n'.join(lines)