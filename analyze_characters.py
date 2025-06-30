"""Character analysis module for identifying characters and their mentions in text."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from api_client import UnifiedLLMClient

from utils import (
    load_text_file, save_json_file,
    normalize_text, find_text_position, cache_result,
    safe_api_call, APIError, FileError
)

# Moved to utils.py

def find_first_mention(text: str, name: str) -> Optional[Dict[str, Any]]:
    """Find first mention of a name in text and return its position info.
    
    Args:
        text: The text to search in
        name: The name to search for
        
    Returns:
        Dictionary with position information or None if not found
    """
    return find_text_position(text, name)

def load_chapter(file_path: str) -> str:
    """Load chapter text from file.
    
    Args:
        file_path: Path to the text file to load
        
    Returns:
        The text content of the file
        
    Raises:
        FileError: If the file can't be loaded
    """
    return load_text_file(file_path)



@safe_api_call
@cache_result()
def analyze_characters(text: str, model: Optional[str] = None) -> Dict[str, Any]:
    """Analyze text to identify characters and their mentions.
    
    Args:
        text: The text to analyze
        model: The model to use (optional, uses provider default if not specified)
        
    Returns:
        Dictionary containing character analysis
        
    Raises:
        APIError: If there's an issue with the API call
    """
    client = UnifiedLLMClient()
    
    system_prompt = """You are a literary analysis assistant specialized in character identification.
Your task is to identify characters and their mentions in text.
Follow these rules strictly:
1. Use EXACT string positions from the provided text
2. Double-check all positions before including them
3. Only include mentions you are 100% certain about
4. Include the complete context sentence for each mention
5. Output valid JSON matching the schema exactly"""

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
    
    response = client.complete(
        messages=messages,
        model=model,
        temperature=0,
        response_format={"type": "json_object"}
    )
    
    # Parse response - unified client returns APIResponse
    content = response.content
    
    try:
        analysis = json.loads(content)
    except json.JSONDecodeError:
        raise APIError("Failed to parse API response as JSON")
    
    # Validate basic structure
    if not isinstance(analysis, dict) or 'characters' not in analysis:
        raise APIError("API response missing required 'characters' object")
        
    # Add metadata
    analysis['metadata'] = {
        "version": "0.2.0",
        "timestamp": datetime.utcnow().isoformat(),
        "character_count": len(analysis['characters']),
        "model": model
    }
    
    return analysis

def save_analysis(analysis: Dict[str, Any], output_file: str) -> None:
    """Save analysis to JSON file.
    
    Args:
        analysis: The analysis data to save
        output_file: Path to save the analysis to
        
    Raises:
        FileError: If the file can't be saved
    """
    save_json_file(analysis, output_file)

def analyze_text_file(file_path: str, output_path: str = None, model: str = "gpt-4") -> Dict[str, Any]:
    """Analyze a text file to identify characters and their mentions.
    
    Args:
        file_path: Path to the text file to analyze
        output_path: Optional path to save the analysis results
        model: The OpenAI model to use
        
    Returns:
        Dictionary containing character analysis
        
    Raises:
        FileError: If there's an issue with the input or output files
        APIError: If there's an issue with the API call
    """
    # Load text
    text = load_chapter(file_path)
    
    # Get analysis
    print(f"Using model: {model}")
    analysis = analyze_characters(text, model)
    
    # Save results if output path provided
    if output_path:
        save_analysis(analysis, output_path)
        print(f"Analysis saved to {output_path}")
    
    # Print summary
    char_count = len(analysis.get('characters', {}))
    print(f"\nFound {char_count} characters:")
    for name, char in analysis.get('characters', {}).items():
        mention_count = len(char.get('mentions', []))
        print(f"- {name}: {mention_count} mentions")
    
    return analysis


def main():
    """Command-line entry point for character analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze characters in a text file")
    parser.add_argument("file_path", help="Path to the text file to analyze")
    parser.add_argument("-o", "--output", help="Path to save the analysis results")
    parser.add_argument("-m", "--model", default="gpt-4", help="OpenAI model to use (default: gpt-4)")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching of API responses")
    args = parser.parse_args()
    
    # Set default output path if not provided
    output_path = args.output
    if not output_path:
        input_path = Path(args.file_path)
        output_path = input_path.with_suffix('.analysis.json')
    
    try:
        # If cache is disabled, temporarily rename the cache directory
        if args.no_cache:
            import os
            from pathlib import Path
            cache_dir = Path(".cache")
            if cache_dir.exists():
                temp_cache_dir = Path(".cache_disabled")
                os.rename(cache_dir, temp_cache_dir)
        
        # Run analysis
        analyze_text_file(args.file_path, str(output_path), args.model)
        
        # Restore cache directory if it was renamed
        if args.no_cache and 'temp_cache_dir' in locals():
            os.rename(temp_cache_dir, cache_dir)
            
    except (FileError, APIError) as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
