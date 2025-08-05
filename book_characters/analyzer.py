"""Character analysis module using only LLM (no regex scanning)."""

import json
from typing import Dict, Any, Optional, List, Tuple
from api_client import UnifiedLLMClient
from book_transform.utils import safe_api_call, cache_result, APIError
from .prompts import get_character_analysis_prompt
from .smart_chunked_analyzer import analyze_book_characters_smart_chunks


@safe_api_call
@cache_result()
def analyze_characters(text: str, model: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """Analyze text to identify characters using LLM only.
    
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
    
    # Get appropriate prompt based on model capabilities
    system_prompt, user_prompt = get_character_analysis_prompt(
        text=text,
        model=model,
        provider=provider
    )
    
    print("Analyzing text for character identification...")
    
    # Use the unified client to create completion
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # Build kwargs - always use high-quality settings
    kwargs = {
        "messages": messages,
        "model": model,
        "temperature": 0.0
    }
    
    # Always request JSON output for consistency
    kwargs["response_format"] = {"type": "json_object"}
    
    # Call the LLM
    response = client.complete(**kwargs)
    
    # Extract characters from response
    try:
        content = response.content.strip()
        
        # Try to parse as JSON
        try:
            analysis = json.loads(content)
        except json.JSONDecodeError:
            # If not valid JSON, try to extract JSON from the response
            analysis = extract_json_from_response(content)
        
        # Ensure we have the expected structure
        if 'characters' not in analysis:
            analysis = {'characters': {}}
            
        print(f"Identified {len(analysis.get('characters', {}))} characters")
        return analysis
        
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        return {'characters': {}}


def extract_json_from_response(content: str) -> Dict[str, Any]:
    """Extract JSON from LLM response that may contain extra text."""
    # Look for JSON structure in the response
    import re
    
    # Try to find JSON object
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # If no valid JSON found, return empty structure
    return {'characters': {}}


def get_full_text_from_json(book_data: Dict[str, Any]) -> str:
    """Extract full text from JSON book for character analysis."""
    full_text = []
    
    for chapter in book_data['chapters']:
        # Add chapter title if present
        if chapter.get('title'):
            full_text.append(f"\nCHAPTER: {chapter['title']}\n")
        
        # Process paragraphs
        for paragraph in chapter['paragraphs']:
            para_text = ' '.join(paragraph.get('sentences', []))
            full_text.append(para_text)
    
    return '\n'.join(full_text)


def analyze_book_characters(book_data: Dict[str, Any], 
                          model: Optional[str] = None,
                          provider: Optional[str] = None,
                          sample_size: int = 50000,
                          verbose: bool = True) -> Tuple[Dict[str, Any], str]:
    """
    Analyze characters in a book using LLM only.
    
    Args:
        book_data: JSON book data
        model: Model to use for analysis
        provider: LLM provider to use
        sample_size: Maximum characters to sample for analysis (ignored for chunked processing)
        verbose: Whether to print progress
        
    Returns:
        Tuple of (character_dict, character_context_string)
    """
    if verbose:
        print("Analyzing characters using LLM...")
    
    try:
        # Analyze in one pass or with smart sampling
        full_text = get_full_text_from_json(book_data)
        
        if verbose:
            print(f"  Book length: {len(full_text)} characters")
        
        # For very long books, we might need to chunk even for API providers
        # Check context window limits
        from book_transform.model_config_loader import get_verified_model_config
        config = get_verified_model_config(model, provider)
        
        if config:
            # Estimate tokens (roughly 4 chars per token)
            estimated_tokens = len(full_text) // 4
            max_context = config.context_window
            
            # Leave room for prompt and response
            # For Grok, we can use more of the context
            if provider == 'grok':
                usable_context = int(max_context * 0.85)  # 85% for Grok
            else:
                usable_context = int(max_context * 0.7)   # 70% for others
            
            if estimated_tokens > usable_context:
                if verbose:
                    print(f"  Book too long for single analysis ({estimated_tokens} tokens > {usable_context} usable)")
                    print("  Using chunked processing...")
                
                # Use chunked processing
                from .api_chunked_analyzer import analyze_book_characters_chunked_api
                characters, character_context = analyze_book_characters_chunked_api(
                    book_data=book_data,
                    model=model,
                    provider=provider,
                    max_tokens_per_chunk=usable_context,
                    verbose=verbose
                )
                
                return characters, character_context
        
        # Book fits in context window - but use smart chunking for better results with Grok
        if provider == 'grok':
            if verbose:
                print("  Using smart chunking for comprehensive analysis...")
            
            # Use smart chunking for better coverage
            characters, character_context = analyze_book_characters_smart_chunks(
                book_data=book_data,
                model=model,
                provider=provider,
                verbose=verbose
            )
            
            return characters, character_context
        else:
            # Other providers - analyze directly
            if verbose:
                print("  Analyzing full text with LLM...")
            
            character_analysis = analyze_characters(full_text, model=model, provider=provider)
            characters = character_analysis.get('characters', {})
        
        # Create character context
        from .context import create_character_context
        character_context = create_character_context(characters)
        
        if verbose:
            print(f"  Found {len(characters)} characters")
            if characters:
                # Show first 5 characters
                char_names = list(characters.keys())[:5]
                print(f"  Sample characters: {', '.join(char_names)}")
                if len(characters) > 5:
                    print(f"  ... and {len(characters) - 5} more")
        
        return characters, character_context
        
    except Exception as e:
        if verbose:
            print(f"Error during character analysis: {e}")
        
        # Return empty results on error
        return {}, "No characters identified"