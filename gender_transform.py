#!/usr/bin/env python3
"""
Gender transformation module v2 with multi-provider support.

This version supports both OpenAI and Grok APIs through a unified interface.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from utils import (
    load_text_file, save_text_file, get_llm_client,
    cache_result, safe_api_call, APIError, FileError
)
from api_client import UnifiedLLMClient, APIResponse

# Import pronoun validator
try:
    from pronoun_validator import validate_transformed_text
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False

# Transformation types (same as original)
TRANSFORM_TYPES = {
    "feminine": {
        "name": "Feminine",
        "description": "Transform text to use feminine pronouns and gender references",
        "changes": [
            "'Mr.' to 'Ms.'", 
            "'he/him/his' to 'she/her/her'",
            "'man/men' to 'woman/women'",
            "'husband' to 'wife'",
            "'father' to 'mother'",
            "'gentleman' to 'lady'"
        ]
    },
    "masculine": {
        "name": "Masculine",
        "description": "Transform text to use masculine pronouns and gender references",
        "changes": [
            "'Ms./Mrs./Miss' to 'Mr.'", 
            "'she/her/her' to 'he/him/his'",
            "'woman/women' to 'man/men'",
            "'wife' to 'husband'",
            "'mother' to 'father'",
            "'lady' to 'gentleman'"
        ]
    },
    "neutral": {
        "name": "Gender-neutral",
        "description": "Transform text to use gender-neutral pronouns and references",
        "changes": [
            "'Mr./Ms./Mrs./Miss' to 'Mx.'",
            "'he/him/his' and 'she/her/her' to 'they/them/their'",
            "'man/woman' to 'person'",
            "'husband/wife' to 'spouse/partner'",
            "'father/mother' to 'parent'",
            "'gentleman/lady' to 'individual'"
        ]
    }
}


def create_transformation_prompt(text: str, transform_type: str, character_context: Optional[str] = None) -> str:
    """Create the transformation prompt for the LLM."""
    
    transform_info = TRANSFORM_TYPES[transform_type]
    changes_list = '\n'.join(f"  - {change}" for change in transform_info['changes'])
    
    prompt = f"""Transform the following text to use {transform_info['name'].lower()} gender representation.

Key changes to make:
{changes_list}

IMPORTANT RULES:
1. Transform ALL gendered language consistently throughout the text
2. Maintain the original meaning, tone, and style
3. Keep all punctuation, formatting, and paragraph structure EXACTLY as in the original
4. Do not add or remove any content
5. Make the transformations sound natural in context
6. Be consistent - if a character is transformed to feminine, ALL references to that character should be feminine

Text to transform:
{text}

Return your response in the following JSON format:
{{
    "transformed_text": "the complete transformed text",
    "changes_made": ["list of specific changes made"],
    "characters_affected": ["list of character names whose gender was changed"]
}}"""

    if character_context:
        prompt = f"""Based on this character analysis:
{character_context}

{prompt}"""
    
    return prompt


@safe_api_call
@cache_result(cache_dir=".cache/transformations")
def transform_text_with_llm(text: str, transform_type: str, 
                           character_context: Optional[str] = None,
                           model: Optional[str] = None,
                           provider: Optional[str] = None) -> Dict[str, Any]:
    """Transform text using the specified LLM provider.
    
    Args:
        text: Text to transform
        transform_type: Type of transformation
        character_context: Optional character analysis context
        model: Optional model override
        provider: Optional provider override ('openai' or 'grok')
        
    Returns:
        Dictionary with transformation results
    """
    client = get_llm_client(provider)
    
    prompt = create_transformation_prompt(text, transform_type, character_context)
    
    messages = [
        {
            "role": "system",
            "content": "You are a literary transformation assistant that modifies gender representation in text while preserving the original style and meaning."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    # Call the LLM
    response = client.complete(
        messages=messages,
        model=model,
        temperature=0,
        response_format={"type": "json_object"} if client.get_provider() == "openai" else None
    )
    
    # Parse the response
    try:
        result = json.loads(response.content)
        
        # Add provider info
        result['provider'] = client.get_provider()
        result['model'] = response.model
        
        return result
    except json.JSONDecodeError as e:
        raise APIError(f"Failed to parse LLM response as JSON: {e}\nResponse: {response.content}")


def transform_text_file(input_file: str, output_file: str, transform_type: str,
                       analysis_file: Optional[str] = None,
                       model: Optional[str] = None,
                       provider: Optional[str] = None) -> Dict[str, Any]:
    """Transform gender representation in a text file.
    
    Args:
        input_file: Path to input text file
        output_file: Path to output text file
        transform_type: Type of transformation
        analysis_file: Optional character analysis file
        model: Optional model override
        provider: Optional provider override ('openai' or 'grok')
        
    Returns:
        Transformation results
    """
    # Load the text
    text = load_text_file(input_file)
    
    # Load character context if provided
    character_context = None
    if analysis_file:
        try:
            with open(analysis_file, 'r') as f:
                analysis_data = json.load(f)
                # Format character information
                char_lines = []
                for char_name, char_info in analysis_data.get('characters', {}).items():
                    gender = char_info.get('gender', 'unknown')
                    role = char_info.get('role', 'character')
                    char_lines.append(f"- {char_name}: {gender} ({role})")
                if char_lines:
                    character_context = "Characters in the text:\n" + '\n'.join(char_lines)
        except Exception as e:
            print(f"Warning: Could not load character analysis: {e}")
    
    # Transform the text
    result = transform_text_with_llm(
        text, 
        transform_type, 
        character_context,
        model=model,
        provider=provider
    )
    
    # Validate if available
    if VALIDATOR_AVAILABLE and 'transformed_text' in result:
        validation_results = validate_transformed_text(
            text,
            result['transformed_text'],
            transform_type
        )
        result['validation'] = validation_results
    
    # Save the transformed text
    save_text_file(result['transformed_text'], output_file)
    
    # Add file information
    result['input_file'] = input_file
    result['output_file'] = output_file
    result['transform_type'] = transform_type
    
    return result


def transform_gender_with_context(text: str, transform_type: str, character_context: str, 
                                model: Optional[str] = None) -> Tuple[str, List[str]]:
    """
    Compatibility wrapper for the original gender_transform interface.
    
    Args:
        text: Text to transform
        transform_type: Type of transformation (feminine/masculine/neutral)
        character_context: Character information for context
        model: Optional model override
        
    Returns:
        Tuple of (transformed_text, changes_made)
    """
    result = transform_text_with_llm(
        text=text,
        transform_type=transform_type,
        character_context=character_context,
        model=model
    )
    
    # Extract transformed text and changes in the format expected by callers
    transformed_text = result.get('transformed_text', text)
    changes_made = result.get('changes_made', [])
    
    return transformed_text, changes_made


def main():
    """CLI entry point for testing."""
    parser = argparse.ArgumentParser(description="Transform gender representation in text")
    parser.add_argument("input", help="Input text file")
    parser.add_argument("output", help="Output text file")
    parser.add_argument("-t", "--type", required=True, 
                       choices=list(TRANSFORM_TYPES.keys()),
                       help="Type of transformation")
    parser.add_argument("-a", "--analysis", help="Character analysis JSON file")
    parser.add_argument("-m", "--model", help="Model override")
    parser.add_argument("-p", "--provider", choices=["openai", "grok"],
                       help="LLM provider to use")
    parser.add_argument("--list-providers", action="store_true",
                       help="List available providers and exit")
    
    args = parser.parse_args()
    
    if args.list_providers:
        from api_client import UnifiedLLMClient
        providers = UnifiedLLMClient.list_available_providers()
        print("Available LLM providers:")
        for provider in providers:
            print(f"  - {provider}")
        return
    
    try:
        result = transform_text_file(
            args.input,
            args.output,
            args.type,
            analysis_file=args.analysis,
            model=args.model,
            provider=args.provider
        )
        
        print(f"✓ Transformation complete using {result['provider']}")
        print(f"  Model: {result['model']}")
        print(f"  Changes made: {len(result.get('changes_made', []))}")
        print(f"  Output: {args.output}")
        
        if 'validation' in result:
            val = result['validation']
            if val['issues_found']:
                print(f"⚠ Validation found {len(val['issues'])} potential issues")
            else:
                print("✓ Validation passed")
                
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    main()