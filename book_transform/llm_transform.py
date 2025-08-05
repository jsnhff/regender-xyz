"""LLM-based text transformation functions."""

import json
from typing import Dict, List, Tuple, Optional, Any

from .utils import safe_api_call, cache_result, APIError
from api_client import get_llm_client

# Transformation types - EXPLICIT modes for consistent results
TRANSFORM_TYPES = {
    "all_male": {
        "name": "All Male",
        "description": "Convert ALL characters to male gender - no exceptions",
        "changes": [
            "ALL titles become 'Mr.' (never Mrs./Ms./Miss/Lady)", 
            "ALL pronouns become 'he/him/his'",
            "ALL gendered terms become male equivalents",
            "'woman/women' to 'man/men'",
            "'wife' to 'husband'",
            "'mother' to 'father'",
            "'daughter' to 'son'",
            "'sister' to 'brother'",
            "'aunt' to 'uncle'",
            "'niece' to 'nephew'",
            "'lady/ladies' to 'gentleman/gentlemen'",
            "Female names to male equivalents (Elizabeth→Elliot, Jane→John, etc.)"
        ]
    },
    "all_female": {
        "name": "All Female",
        "description": "Convert ALL characters to female gender - no exceptions",
        "changes": [
            "ALL titles become 'Ms./Mrs./Miss' (never Mr./Lord/Sir)", 
            "ALL pronouns become 'she/her/her'",
            "ALL gendered terms become female equivalents",
            "'man/men' to 'woman/women'",
            "'husband' to 'wife'",
            "'father' to 'mother'",
            "'son' to 'daughter'",
            "'brother' to 'sister'",
            "'uncle' to 'aunt'",
            "'nephew' to 'niece'",
            "'gentleman/gentlemen' to 'lady/ladies'",
            "Male names to female equivalents (John→Jane, William→Willow, etc.)"
        ]
    },
    "gender_swap": {
        "name": "Gender Swap",
        "description": "Swap the gender of EVERY character - male→female, female→male",
        "changes": [
            "Male titles (Mr./Lord/Sir) → Female titles (Ms./Lady/Dame)",
            "Female titles (Mrs./Ms./Miss/Lady) → Male titles (Mr./Lord/Sir)",
            "'he/him/his' ↔ 'she/her/her'",
            "'man/men' ↔ 'woman/women'",
            "'husband' ↔ 'wife'",
            "'father' ↔ 'mother'",
            "'son' ↔ 'daughter'",
            "'brother' ↔ 'sister'",
            "ALL characters must change gender - no exceptions"
        ]
    }
}


def create_transformation_prompt(text: str, transform_type: str, character_context: Optional[str] = None, json_output: bool = True) -> str:
    """Create the transformation prompt for the LLM."""
    
    transform_info = TRANSFORM_TYPES[transform_type]
    changes_list = '\n'.join(f"  - {change}" for change in transform_info['changes'])
    
    # Create mode-specific instructions
    if transform_type == "all_male":
        critical_instruction = """CRITICAL: EVERY character must be male. No exceptions. 
Do not try to maintain gender balance. Do not keep any female characters.
If you see ANY female pronouns, titles, or gendered terms in your output, you have failed."""
    elif transform_type == "all_female":
        critical_instruction = """CRITICAL: EVERY character must be female. No exceptions.
Do not try to maintain gender balance. Do not keep any male characters.  
If you see ANY male pronouns, titles, or gendered terms in your output, you have failed."""
    else:  # gender_swap
        critical_instruction = """CRITICAL: EVERY character must swap gender. No exceptions.
Male characters become female. Female characters become male.
No character should keep their original gender. Every single character must change."""
    
    prompt = f"""Transform the following text: {transform_info['description']}

{critical_instruction}

Required changes:
{changes_list}

TRANSFORMATION RULES:
1. Transform ALL gendered language according to the mode
2. Maintain the original meaning, tone, and style
3. Keep all punctuation, formatting, and paragraph structure EXACTLY as in the original
4. Do not add or remove any content
5. Make the transformations sound natural in context
6. For {transform_type}: {transform_info['description']}

Text to transform:
{text}

"""
    
    if json_output:
        prompt += """Return your response in the following JSON format:
{{
    "transformed_text": "the complete transformed text",
    "changes_made": ["list of specific changes made"],
    "characters_affected": ["list of character names whose gender was changed"]
}}

CRITICAL JSON FORMATTING RULES:
1. All quotes inside the "transformed_text" field MUST be escaped with backslashes (\" not ")
2. Return ONLY the JSON object - no other text before or after
3. The JSON must be valid and parseable
4. Example: "She said \"Hello\" to him" (correct) vs "She said "Hello" to him" (incorrect)"""
    else:
        prompt += "Return ONLY the transformed text. Do not include any explanation, JSON formatting, or additional fields - just the transformed text itself."

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
    
    # Determine if we should ask for JSON output
    # Due to JSON parsing issues with Grok, let's use plain text for now
    json_output = client.get_provider() in ["openai"]
    
    prompt = create_transformation_prompt(text, transform_type, character_context, json_output)
    
    messages = [
        {
            "role": "system",
            "content": "You are a literary transformation assistant that modifies gender representation in text while preserving the original style and meaning. Always return valid JSON when requested."
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
    
    # Only add response_format for providers that support it properly
    if client.get_provider() in ["openai"]:
        kwargs["response_format"] = {"type": "json_object"}
    
    response = client.complete(**kwargs)
    
    # Parse the response
    try:
        # For providers that support JSON mode, try parsing as JSON
        if client.get_provider() in ["openai"]:
            result = json.loads(response.content)
            
            # Add provider info
            result['provider'] = client.get_provider()
            result['model'] = response.model
            
            return result
        else:
            # For MLX and others, we get plain text back
            # Return a simplified result
            return {
                'transformed_text': response.content.strip(),
                'changes_made': [],  # We don't track individual changes in plain text mode
                'characters_affected': [],  # We don't track affected characters in plain text mode
                'provider': client.get_provider(),
                'model': response.model
            }
    except json.JSONDecodeError as e:
        # For all providers, try to extract JSON from response
        # This helps handle cases where the LLM doesn't follow instructions perfectly
        if True:  # Always try extraction as fallback
            import re
            # Try to find JSON in the response
            content = response.content.strip()
            
            # If the content starts with {, assume it's all JSON
            if content.startswith('{'):
                try:
                    # Clean up the JSON string
                    json_str = content
                    # Remove any trailing commas before closing braces/brackets
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    # Replace smart quotes with regular quotes
                    json_str = json_str.replace('"', '"').replace('"', '"')
                    json_str = json_str.replace(''', "'").replace(''', "'")
                    
                    # Special handling for the transformed_text field which may contain quotes
                    # Use a more flexible regex that handles multiline content
                    parts = re.search(r'"transformed_text"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"changes_made"\s*:\s*(\[[^\]]*\])\s*,\s*"characters_affected"\s*:\s*(\[[^\]]*\])', json_str, re.DOTALL)
                    if parts:
                        text_content = parts.group(1)
                        changes_content = parts.group(2)
                        chars_content = parts.group(3)
                        
                        # Fix common issues in arrays
                        # Add missing closing quotes
                        changes_content = re.sub(r'([^\\])"([^",\]]+)(?=,|\])', r'\1"\2"', changes_content)
                        chars_content = re.sub(r'([^\\])"([^",\]]+)(?=,|\])', r'\1"\2"', chars_content)
                        
                        try:
                            # Build a clean JSON object
                            result = {
                                "transformed_text": text_content,
                                "changes_made": json.loads(changes_content),
                                "characters_affected": json.loads(chars_content)
                            }
                            result['provider'] = client.get_provider()
                            result['model'] = response.model
                            return result
                        except json.JSONDecodeError:
                            pass
                    
                    # Fallback to direct parsing
                    result = json.loads(json_str)
                    result['provider'] = client.get_provider()
                    result['model'] = response.model
                    return result
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            # Fallback to regex extraction
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                try:
                    # Clean up the JSON string
                    json_str = json_match.group(0)
                    # Remove any trailing commas before closing braces/brackets
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    # Replace smart quotes with regular quotes
                    json_str = json_str.replace('"', '"').replace('"', '"')
                    json_str = json_str.replace(''', "'").replace(''', "'")
                    # Escape quotes inside the text fields
                    # This is a bit hacky but works for the common case
                    json_str = re.sub(r'("transformed_text":\s*"[^"]*)"([^"]*"[^"]*")', r'\1\"\2', json_str)
                    
                    result = json.loads(json_str)
                    result['provider'] = client.get_provider()
                    result['model'] = response.model
                    return result
                except json.JSONDecodeError:
                    pass
        
        raise APIError(f"Failed to parse LLM response as JSON: {e}\nResponse: {response.content}")


def transform_gender_with_context(text: str, transform_type: str, character_context: str, 
                                model: Optional[str] = None) -> Tuple[str, List[str]]:
    """
    Transform gender in the provided text.
    
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