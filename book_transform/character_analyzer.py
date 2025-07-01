"""Character analysis module for book transformation."""

import json
import re
from typing import Dict, Any, Optional, List
from api_client import UnifiedLLMClient
from .utils import safe_api_call, cache_result, APIError


@safe_api_call
@cache_result()
def analyze_characters(text: str, model: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """Analyze text to identify characters and their mentions.
    
    Args:
        text: The text to analyze
        model: The model to use (optional, uses provider default if not specified)
        provider: The LLM provider to use (optional)
        
    Returns:
        Dictionary containing character analysis
        
    Raises:
        APIError: If there's an issue with the API call
    """
    client = UnifiedLLMClient(provider=provider)
    
    # Adjust prompt based on provider - MLX models need simpler instructions
    if client.get_provider() == 'mlx':
        system_prompt = """You are a character analysis assistant. Identify characters in the text and output valid JSON."""
    else:
        system_prompt = """You are a literary analysis assistant specialized in character identification.
Your task is to identify characters and their mentions in text.
Follow these rules strictly:
1. Use EXACT string positions from the provided text
2. Double-check all positions before including them
3. Only include mentions you are 100% certain about
4. Include the complete context sentence for each mention
5. Output valid JSON matching the schema exactly"""

    # Simplify prompt for MLX models
    if client.get_provider() == 'mlx':
        user_prompt = f"""Analyze this text and identify the main characters.

For each character, provide:
- name: their name
- gender: male or female
- role: brief description

Output as JSON with this exact structure:
{{
    "characters": {{
        "Character Name": {{
            "name": "Character Name",
            "gender": "male or female",
            "role": "brief description",
            "mentions": [],
            "name_variants": []
        }}
    }}
}}

Text to analyze:
{text[:2000]}  # Limit text for MLX

Respond ONLY with valid JSON."""
    else:
        user_prompt = f"""Analyze this text and create a JSON object with character analysis.
For each character, carefully locate:
1. Their name mentions (exact matches only)
2. Clear pronoun references (he/she/him/her)
3. Clear possessive references (his/her)

IMPORTANT: For each mention, you must:
1. Find the exact start position by counting characters from the start
2. Calculate the end position as (start + len(mention_text))
3. Include the full sentence containing the mention as context
4. Verify the text at those positions matches exactly

Required JSON structure:
{{
    "characters": {{
        "Character Name": {{
            "name": "Character Name",
            "gender": "male or female",
            "role": "brief description",
            "mentions": [
                {{
                    "start": <integer position in text>,
                    "end": <integer position in text>,
                    "text": "exact mention text",
                    "context": "full sentence containing mention",
                    "mention_type": "name or pronoun or possessive"
                }}
            ],
            "name_variants": ["list", "of", "variations"]
        }}
    }}
}}

Text to analyze:
{text}

Output valid JSON only."""

    print("Analyzing text for character identification...")
    
    # Use the unified client to create completion
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # MLX models might not support response_format parameter
    kwargs = {
        "messages": messages,
        "model": model,
        "temperature": 0
    }
    
    # Only add response_format for providers that support it
    if client.get_provider() != 'mlx':
        kwargs["response_format"] = {"type": "json_object"}
    
    response = client.complete(**kwargs)
    
    try:
        # Parse the JSON response
        if hasattr(response, 'json_content'):
            analysis = response.json_content
        else:
            # For MLX and other providers, we need to parse manually
            content = response.content
            
            # Try to parse the response
            try:
                analysis = json.loads(content)
            except json.JSONDecodeError as e:
                # If MLX model, try to extract JSON from the response
                if client.get_provider() == 'mlx':
                    # Try to extract JSON from the response
                    # First, try to find JSON boundaries
                    start_idx = content.find('{')
                    if start_idx != -1:
                        # Try to parse from each { to find valid JSON
                        for i in range(start_idx, len(content)):
                            if content[i] == '{':
                                # Count braces to find matching closing brace
                                brace_count = 0
                                for j in range(i, len(content)):
                                    if content[j] == '{':
                                        brace_count += 1
                                    elif content[j] == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            # Found matching closing brace
                                            json_str = content[i:j+1]
                                            try:
                                                analysis = json.loads(json_str)
                                                # Verify it has the expected structure
                                                if 'characters' in analysis:
                                                    break
                                            except json.JSONDecodeError:
                                                continue
                                            break
                        else:
                            # If no valid JSON found, create fallback
                            print(f"Warning: MLX model failed to generate valid JSON for character analysis")
                            analysis = {'characters': {}}
                    else:
                        print(f"Warning: Could not find JSON in MLX response")
                        analysis = {'characters': {}}
                else:
                    # For other providers, re-raise the error
                    raise APIError(f"Failed to parse character analysis response: {e}")
        
        # Validate the structure
        if 'characters' not in analysis:
            analysis = {'characters': {}}
            
        print(f"Identified {len(analysis['characters'])} characters")
        
        return analysis
        
    except json.JSONDecodeError as e:
        raise APIError(f"Failed to parse character analysis response: {e}")
    except Exception as e:
        # For any other errors, provide helpful context
        print(f"Error during character analysis: {e}")
        if client.get_provider() == 'mlx':
            print("Note: MLX models may have difficulty generating complex JSON structures.")
            print("Consider using a different model for character analysis.")
        raise


def get_full_text_from_json(book_data: Dict[str, Any]) -> str:
    """Extract full text from JSON book for character analysis."""
    full_text = []
    
    for chapter in book_data['chapters']:
        # Add chapter title if present
        if chapter.get('title'):
            full_text.append(chapter['title'])
        
        # Handle both old (flat sentences) and new (paragraphs) structures
        if 'paragraphs' in chapter:
            # New structure with paragraphs
            for paragraph in chapter['paragraphs']:
                full_text.extend(paragraph.get('sentences', []))
        elif 'sentences' in chapter:
            # Old structure with flat sentences
            full_text.extend(chapter['sentences'])
    
    return '\n'.join(full_text)


def create_character_context(characters: Dict[str, Any]) -> str:
    """Create a character context string for transformations."""
    if not characters:
        return ""
    
    context_parts = ["Known characters:"]
    for name, info in characters.items():
        gender = info.get('gender', 'unknown')
        context_parts.append(f"- {name}: {gender}")
    
    return '\n'.join(context_parts)


def analyze_book_characters(book_data: Dict[str, Any], 
                          model: str = "gpt-4o-mini",
                          provider: Optional[str] = None,
                          sample_size: int = 50000,
                          verbose: bool = True) -> tuple[Dict[str, Any], str]:
    """
    Analyze characters in a book.
    
    Args:
        book_data: JSON book data
        model: Model to use for analysis
        provider: LLM provider to use
        sample_size: Maximum characters to sample for analysis
        verbose: Whether to print progress
        
    Returns:
        Tuple of (character_dict, character_context_string)
    """
    if verbose:
        print("Analyzing characters...")
    
    # First, do a fast scan to identify potential characters
    from .fast_character_scanner import fast_scan_for_characters, get_character_sentences
    
    # Fast scan the entire book
    initial_characters = fast_scan_for_characters(book_data, verbose=verbose)
    
    # If we found characters with the fast scan, get relevant sentences only
    if initial_characters:
        # Get only sentences that mention characters (much smaller dataset)
        relevant_sentences = get_character_sentences(book_data, initial_characters, max_sentences=500)
        text_sample = '\n'.join(relevant_sentences)
        
        if verbose:
            print(f"  Using {len(relevant_sentences)} character-relevant sentences for detailed analysis")
    else:
        # Fallback to original sampling method
        full_text = get_full_text_from_json(book_data)
        
        # Sample text if too large
        if len(full_text) > sample_size:
            # Take beginning, middle, and end samples
            text_sample = (
                full_text[:sample_size//3] + 
                full_text[len(full_text)//2 - sample_size//6:len(full_text)//2 + sample_size//6] +
                full_text[-sample_size//3:]
            )
        else:
            text_sample = full_text
    
    try:
        # For MLX or if we already have good character data, use a simpler approach
        if provider == 'mlx' and initial_characters:
            # Convert fast scan results to the expected format
            characters = {}
            for name, info in initial_characters.items():
                characters[name] = {
                    'name': name,
                    'gender': info['gender'],
                    'role': f"Character appearing {info['mentions']} times",
                    'mentions': [],  # Skip detailed mentions for MLX
                    'name_variants': info.get('variants', [])
                }
            
            character_context = create_character_context(characters)
            
            if verbose:
                print(f"  Using fast-scan results: {len(characters)} characters")
                if characters:
                    print(f"  Main characters: {', '.join(list(characters.keys())[:10])}")
            
            return characters, character_context
        else:
            # Use LLM for more detailed analysis on the filtered text
            character_analysis = analyze_characters(text_sample, model=model, provider=provider)
            characters = character_analysis.get('characters', {})
            character_context = create_character_context(characters)
            
            if verbose:
                print(f"  Found {len(characters)} characters")
                if characters:
                    print(f"  Main characters: {', '.join(list(characters.keys())[:5])}")
            
            return characters, character_context
        
    except Exception as e:
        if verbose:
            print(f"Warning: Character analysis failed: {e}")
            if initial_characters:
                print("Falling back to fast-scan results")
                # Use fast scan results as fallback
                characters = {}
                for name, info in initial_characters.items():
                    characters[name] = {
                        'name': name,
                        'gender': info['gender'],
                        'role': f"Character appearing {info['mentions']} times",
                        'mentions': [],
                        'name_variants': info.get('variants', [])
                    }
                return characters, create_character_context(characters)
            else:
                print("Proceeding without character context")
        return {}, ""