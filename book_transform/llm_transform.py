"""LLM-based text transformation functions."""

import json
from typing import Dict, List, Tuple, Optional, Any

from .utils import safe_api_call, cache_result, APIError
from api_client import get_llm_client

# Transformation types
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
    kwargs = {
        "messages": messages,
        "model": model,
        "temperature": 0
    }
    
    # Only add response_format for providers that support it
    if client.get_provider() in ["openai", "grok"]:
        kwargs["response_format"] = {"type": "json_object"}
    
    response = client.complete(**kwargs)
    
    # Parse the response
    try:
        result = json.loads(response.content)
        
        # Add provider info
        result['provider'] = client.get_provider()
        result['model'] = response.model
        
        return result
    except json.JSONDecodeError as e:
        # For MLX, try to extract JSON from response
        if client.get_provider() == 'mlx':
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response.content, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                    result['provider'] = client.get_provider()
                    result['model'] = response.model
                    return result
                except json.JSONDecodeError:
                    pass
        
        raise APIError(f"Failed to parse LLM response as JSON: {e}\nResponse: {response.content}")


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