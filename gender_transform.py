#!/usr/bin/env python3
"""
Gender transformation module for modifying gender representation in text.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from openai import OpenAI

from utils import (
    load_text_file, save_text_file, get_openai_client,
    cache_result, safe_api_call, APIError, FileError
)

# Import pronoun validator
try:
    from pronoun_validator import validate_transformed_text
    VALIDATOR_AVAILABLE = True
except ImportError:
    VALIDATOR_AVAILABLE = False

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
        "description": "Transform text to use gender-neutral language with Mx. as the title",
        "changes": [
            "'Mr./Ms./Mrs./Miss' to 'Mx.'", 
            "'he/she' to 'they'",
            "'him/her' to 'them'",
            "'his/her' to 'their'",
            "Gender-specific terms to neutral alternatives"
        ]
    }
}

@safe_api_call
@cache_result()
def transform_gender(text: str, transform_type: str, model: str = "gpt-4") -> Tuple[str, List[str]]:
    """Transform text to use specified gender pronouns and references.
    
    Args:
        text: The text to transform
        transform_type: Type of transformation (feminine, masculine, neutral)
        model: The OpenAI model to use
        
    Returns:
        Tuple containing (transformed_text, list_of_changes)
        
    Raises:
        ValueError: If the transform type is invalid
        APIError: If there's an issue with the API call
    """
    if transform_type not in TRANSFORM_TYPES:
        raise ValueError(f"Invalid transform type: {transform_type}. "  
                         f"Must be one of: {', '.join(TRANSFORM_TYPES.keys())}")
    
    client = get_openai_client()
    transform_info = TRANSFORM_TYPES[transform_type]
    
    system_prompt = f"""
    You are an expert at gender transformation in literature.
    Your task is to transform text to use {transform_info['name'].lower()} pronouns and gender references.
    Follow these rules:
    1. Change character gender references appropriately
    2. Adjust all gendered terms consistently
    3. Keep proper names but change pronouns referring to them
    4. Maintain the original writing style and flow
    5. Be thorough - don't miss any gendered references
    6. Pay special attention to possessive pronouns in relationship contexts (e.g., 'his wife' → 'her wife' when the subject is feminine)
    7. Ensure complete consistency in pronoun usage throughout the text
    8. Double-check all instances of 'his', 'her', 'him', 'she', 'he' to ensure they match the intended gender
    9. For neutral transformations, replace 'Mr./Mrs./Ms./Miss' with 'Mx.' rather than removing titles completely
    10. Return your response as a valid JSON object
    """
    
    user_prompt = f"""
    {transform_info['description']}.
    Make these specific changes:
    {chr(10).join(f"{i+1}. Change {change}" for i, change in enumerate(transform_info['changes']))}
    
    IMPORTANT: If this is a neutral transformation, replace all instances of Mr., Mrs., Ms., and Miss with Mx. 
    For example: "Mr. Bennet" should become "Mx. Bennet" NOT just "Bennet".
    
    Return your response as a json object in this exact format:
    {{
        "text": "<the transformed text>",
        "changes": ["Changed X to Y", ...]
    }}
    
    Text to transform:
    {text}
    """
    
    print(f"Applying {transform_info['name']} transformation using model: {model}...")
    
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    
    try:
        result = json.loads(response.choices[0].message.content)
        if 'text' not in result or 'changes' not in result:
            raise APIError("API response missing required fields: 'text' and/or 'changes'")
        return result['text'], result['changes']
    except json.JSONDecodeError as e:
        raise APIError(f"Failed to parse API response as JSON: {e}")
    except KeyError as e:
        raise APIError(f"Missing required field in API response: {e}")

@safe_api_call
@cache_result()
def verify_transformation(text: str, target_gender: str, model: str = "gpt-4") -> List[Dict[str, str]]:
    """Verify that a gender transformation was applied correctly.
    
    Args:
        text: The transformed text to verify
        target_gender: The target gender of the transformation (feminine, masculine, neutral)
        model: The OpenAI model to use
        
    Returns:
        List of dictionaries containing missed transformations with context
        
    Raises:
        ValueError: If the target gender is invalid
        APIError: If there's an issue with the API call
    """
    if target_gender not in TRANSFORM_TYPES:
        raise ValueError(f"Invalid target gender: {target_gender}. "  
                         f"Must be one of: {', '.join(TRANSFORM_TYPES.keys())}")
    
    client = get_openai_client()
    
    opposite_genders = {
        "feminine": "male",
        "masculine": "female",
        "neutral": "gendered"
    }
    
    check_for = opposite_genders[target_gender]
    
    system_prompt = f"""
    You are an expert at finding gendered language in text.
    Your task is to identify any remaining {check_for} pronouns or gender references.
    Be thorough and catch subtle references.
    """
    
    user_prompt = f"""
    Check this text for any remaining {check_for} pronouns or gender references.
    Return a JSON array of objects with the following structure:
    [{{
        "reference": "the {check_for} reference found",
        "context": "the surrounding text with the reference",
        "suggestion": "suggested replacement"
    }}]
    
    If no {check_for} references are found, return an empty array.
    
    Text to check:
    {text}
    """
    
    print(f"Verifying {target_gender} transformation using model: {model}...")
    
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    
    try:
        result = json.loads(response.choices[0].message.content)
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "references" in result:
            return result["references"]
        else:
            return []
    except json.JSONDecodeError as e:
        raise APIError(f"Failed to parse verification response as JSON: {e}")

def transform_text_file(file_path: str, transform_type: str, output_path: str = None, model: str = "gpt-4", **options) -> Tuple[str, List[str]]:
    """Transform gender representation in a text file.
    
    Args:
        file_path: Path to the text file to transform
        transform_type: Type of transformation (feminine, masculine, neutral)
        output_path: Optional path to save the transformed text
        model: The OpenAI model to use
        
    Returns:
        Tuple containing (transformed_text, list_of_changes)
        
    Raises:
        FileError: If there's an issue with the input or output files
        APIError: If there's an issue with the API call
        ValueError: If the transform type is invalid
    """
    # Read input text
    text = load_text_file(file_path)
    
    # Transform text
    transformed, changes = transform_gender(text, transform_type, model)
    
    # Apply character name customizations if provided
    character_customizations = options.get('character_customizations', {})
    if character_customizations:
        print("\nApplying character name customizations...")
        for original_name, new_name in character_customizations.items():
            if original_name in transformed:
                transformed = transformed.replace(original_name, new_name)
                changes.append(f"Customized character: '{original_name}' → '{new_name}'")
                print(f"- Changed '{original_name}' to '{new_name}'")
    
    print("\nChanges made:")
    for change in changes:
        print(f"- {change}")
    
    # Apply pronoun validator if available
    if VALIDATOR_AVAILABLE:
        print("\nRunning pronoun consistency validation...")
        corrected_text, corrections = validate_transformed_text(transformed, transform_type)
        
        if corrections:
            print(f"Found {len(corrections)} pronoun inconsistencies:")
            for i, correction in enumerate(corrections, 1):
                print(f"- Changed '{correction['original']}' to '{correction['corrected']}'")
            # Update the transformed text with corrections
            transformed = corrected_text
            # Add the corrections to the changes list
            changes.extend([f"Fixed pronoun: '{c['original']}' to '{c['corrected']}'" for c in corrections])
        else:
            print("No pronoun inconsistencies found.")
    
    # Verify transformation
    missed = verify_transformation(transformed, transform_type, model)
    
    if missed:
        print("\nPotentially missed transformations:")
        for item in missed:
            print(f"- {item['reference']} in context: '{item['context']}'")
            if 'suggestion' in item:
                print(f"  Suggestion: {item['suggestion']}")
    else:
        print("\nNo missed transformations found.")
    
    # Save results if output path provided
    if output_path:
        save_text_file(transformed, output_path)
        print(f"\nTransformed text saved to {output_path}")
    
    return transformed, changes


def main():
    """Command-line entry point for gender transformation."""
    parser = argparse.ArgumentParser(description="Transform gender representation in text")
    parser.add_argument("file_path", help="Path to the text file to transform")
    parser.add_argument(
        "-t", "--type", 
        choices=list(TRANSFORM_TYPES.keys()), 
        default="feminine",
        help="Type of transformation to apply"
    )
    parser.add_argument("-o", "--output", help="Path to save the transformed text")
    parser.add_argument("-m", "--model", default="gpt-4", help="OpenAI model to use (default: gpt-4)")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching of API responses")
    args = parser.parse_args()
    
    # Set default output path if not provided
    output_path = args.output
    if not output_path:
        input_path = Path(args.file_path)
        transform_suffix = f".{args.type}.txt"
        output_path = input_path.with_suffix(transform_suffix)
    
    try:
        # If cache is disabled, temporarily rename the cache directory
        if args.no_cache:
            import os
            cache_dir = Path(".cache")
            if cache_dir.exists():
                temp_cache_dir = Path(".cache_disabled")
                os.rename(cache_dir, temp_cache_dir)
        
        # Run transformation
        transform_text_file(args.file_path, args.type, output_path, args.model)
        
        # Restore cache directory if it was renamed
        if args.no_cache and 'temp_cache_dir' in locals():
            os.rename(temp_cache_dir, cache_dir)
            
    except (FileError, APIError, ValueError) as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
