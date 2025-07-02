#!/usr/bin/env python3
"""
Gender transformation module for modifying gender representation in text.
"""

import json
import argparse
import re
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


def scan_for_gendered_language(text: str, transform_type: str) -> dict:
    """Scan text for remaining gendered language patterns."""
    
    if transform_type == "neutral":
        he_she_matches = re.findall(r'\b(he|she|He|She)\b', text)
        him_her_matches = re.findall(r'\b(him|her|Him|Her)\b', text)
        his_her_matches = re.findall(r'\b(his|her|His|Her)\b', text)
        title_matches = re.findall(r'\b(Mr\.|Mrs\.|Ms\.|Miss)\s+', text)
        
        total_issues = len(he_she_matches + him_her_matches + his_her_matches + title_matches)
        
        return {
            'total_issues': total_issues,
            'he_she': he_she_matches,
            'him_her': him_her_matches,
            'his_her': his_her_matches,
            'titles': title_matches
        }
    
    elif transform_type == "feminine":
        # Look for remaining masculine pronouns and titles
        he_matches = re.findall(r'\b(he|He)\b', text)
        him_matches = re.findall(r'\b(him|Him)\b', text)
        his_matches = re.findall(r'\b(his|His)\b', text)
        mr_matches = re.findall(r'\bMr\.\s+', text)
        
        total_issues = len(he_matches + him_matches + his_matches + mr_matches)
        
        return {
            'total_issues': total_issues,
            'he_she': he_matches,
            'him_her': him_matches,
            'his_her': his_matches,
            'titles': mr_matches
        }
    
    elif transform_type == "masculine":
        # Look for remaining feminine pronouns and titles
        she_matches = re.findall(r'\b(she|She)\b', text)
        her_matches = re.findall(r'\b(her|Her)\b', text)
        female_titles = re.findall(r'\b(Mrs\.|Ms\.|Miss)\s+', text)
        
        total_issues = len(she_matches + her_matches + female_titles)
        
        return {
            'total_issues': total_issues,
            'he_she': she_matches,
            'him_her': her_matches,
            'his_her': [],  # Not applicable for masculine
            'titles': female_titles
        }
    
    return {'total_issues': 0}

def find_specific_errors(text: str, transform_type: str) -> List[Dict[str, str]]:
    """Find specific gendered language errors with context for AI learning."""
    
    errors = []
    
    if transform_type == "neutral":
        # Find gendered pronouns with surrounding context for neutral
        for match in re.finditer(r'\b(he|she|He|She|him|her|Him|Her|his|her|His|Her)\b', text):
            word = match.group()
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end]
            
            # Determine correct replacement
            corrections = {
                'he': 'they', 'He': 'They', 'she': 'they', 'She': 'They',
                'him': 'them', 'Him': 'Them', 'her': 'them', 'Her': 'Them', 
                'his': 'their', 'His': 'Their'
            }
            
            # Special handling for "her" - could be possessive
            if word.lower() == 'her':
                after_word = text[match.end():match.end()+20].strip()
                if re.match(r'^[a-zA-Z]', after_word):
                    corrections[word] = 'their'  # Possessive
                else:
                    corrections[word] = 'them'   # Object pronoun
            
            if word in corrections:
                errors.append({
                    'error': word,
                    'correction': corrections[word],
                    'context': context,
                    'position': match.start(),
                    'type': 'pronoun'
                })
        
        # Find title errors for neutral
        for match in re.finditer(r'\b(Mr\.|Mrs\.|Ms\.|Miss)\s+', text):
            title = match.group().strip()
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context = text[start:end]
            
            errors.append({
                'error': title,
                'correction': 'Mx.',
                'context': context,
                'position': match.start(),
                'type': 'title'
            })
    
    elif transform_type == "feminine":
        # Find masculine pronouns that should be feminine
        for match in re.finditer(r'\b(he|He|him|Him|his|His|Mr\.)\b', text):
            word = match.group()
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end]
            
            # Corrections for feminine transformation
            corrections = {
                'he': 'she', 'He': 'She',
                'him': 'her', 'Him': 'Her',
                'his': 'her', 'His': 'Her',
                'Mr.': 'Ms.'
            }
            
            if word in corrections:
                errors.append({
                    'error': word,
                    'correction': corrections[word],
                    'context': context,
                    'position': match.start(),
                    'type': 'pronoun' if word != 'Mr.' else 'title'
                })
    
    elif transform_type == "masculine":
        # Find feminine pronouns that should be masculine
        for match in re.finditer(r'\b(she|She|her|Her|Mrs\.|Ms\.|Miss)\b', text):
            word = match.group()
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end]
            
            # Corrections for masculine transformation
            corrections = {
                'she': 'he', 'She': 'He',
                'her': 'him', 'Her': 'Him',  # Note: this is simplistic, "her" could be possessive
                'Mrs.': 'Mr.', 'Ms.': 'Mr.', 'Miss': 'Mr.'
            }
            
            if word in corrections:
                errors.append({
                    'error': word,
                    'correction': corrections[word],
                    'context': context,
                    'position': match.start(),
                    'type': 'pronoun' if word not in ['Mrs.', 'Ms.', 'Miss'] else 'title'
                })
    
    return errors

def automatic_qc_pass(text: str, transform_type: str, model: str = "gpt-4") -> Tuple[str, List[str]]:
    """Intelligent QC loop that learns from specific errors and teaches the AI.
    
    Args:
        text: Text from first transformation pass
        transform_type: Type of transformation (neutral, feminine, masculine)
        model: OpenAI model to use
        
    Returns:
        Tuple of (cleaned_text, list_of_additional_changes)
    """
    
    current_text = text
    all_qc_changes = []
    max_iterations = 5
    iteration = 0
    
    print("🧠 Starting AI learning loop until 100% transformation...")
    
    while iteration < max_iterations:
        iteration += 1
        
        # Find specific errors with context
        errors = find_specific_errors(current_text, transform_type)
        
        if not errors:
            print(f"   ✅ LEARNING COMPLETE: 100% transformation achieved after {iteration-1} QC passes")
            break
            
        print(f"   🧠 Learning Pass {iteration}: Found {len(errors)} specific errors to teach AI")
        
        # Process errors for ALL transformation types (not just neutral)
        client = get_openai_client()
        
        # Group errors by type for better learning
        pronoun_errors = [e for e in errors if e['type'] == 'pronoun']
        title_errors = [e for e in errors if e['type'] == 'title']
        
        # Create learning-focused prompt with specific examples
        error_examples = []
        
        if pronoun_errors:
            error_examples.append("PRONOUN ERRORS YOU MISSED:")
            for i, error in enumerate(pronoun_errors[:8], 1):  # Show up to 8 examples
                error_examples.append(f"{i}. '{error['error']}' should be '{error['correction']}' in: ...{error['context']}...")
        
        if title_errors:
            error_examples.append("\nTITLE ERRORS YOU MISSED:")
            for i, error in enumerate(title_errors[:5], 1):  # Show up to 5 examples
                error_examples.append(f"{i}. '{error['error']}' should be '{error['correction']}' in: ...{error['context']}...")
        
        # Create transformation-specific learning rules
        if transform_type == "neutral":
            rules = """GENERALIZED RULES (not just exact matches):
- Any form of he/she referring to a person → they
- Any him/her as object pronoun → them  
- Any his/her as possessive → their
- Any Mr./Mrs./Ms./Miss title → Mx."""
        elif transform_type == "feminine":
            rules = """GENERALIZED RULES (not just exact matches):
- Any form of he referring to a person → she
- Any him as object pronoun → her
- Any his as possessive → her  
- Any Mr. title → Ms."""
        elif transform_type == "masculine":
            rules = """GENERALIZED RULES (not just exact matches):
- Any form of she referring to a person → he
- Any her as object pronoun → him
- Any her as possessive → his
- Any Mrs./Ms./Miss title → Mr."""
        
        learning_prompt = f"""
You are learning from your mistakes. In your previous {transform_type} transformation, you missed {len(errors)} gendered language instances.

{chr(10).join(error_examples)}

LEARNING OBJECTIVES:
1. Study each error above and understand WHY you missed it
2. Look for similar patterns throughout the text
3. Be more systematic about pronoun context (subject vs object vs possessive)
4. Transform ALL titles without exception
5. This is learning pass {iteration} - apply lessons from previous failures

{rules}
- Consider context and grammar, not just word matching

Now fix the text using this learning:

{current_text}

Return JSON with:
{{"text": "corrected text with ALL errors fixed", "changes": ["specific corrections made with reasoning"]}}
"""
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": f"You are learning from {len(errors)} specific errors. Pass {iteration}: Be more intelligent about language patterns."},
                    {"role": "user", "content": learning_prompt}
                ],
                temperature=0.1,  # Low but not zero - allow some linguistic reasoning
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            if 'text' in result and 'changes' in result:
                current_text = result['text']
                qc_changes = [f"Learning{iteration}: {change}" for change in result['changes']]
                all_qc_changes.extend(qc_changes)
                
                print(f"      🎯 AI learned and fixed {len(result['changes'])} issues")
            else:
                print(f"      ❌ Learning pass {iteration} returned invalid response")
                break
                
        except Exception as e:
            print(f"      ❌ Learning pass {iteration} failed: {e}")
            break
    
    # Final check with regex fallback for stubborn titles
    final_scan = scan_for_gendered_language(current_text, transform_type)
    
    if final_scan['total_issues'] > 0 and transform_type == "neutral":
        print(f"🔧 REGEX FALLBACK: Applying direct regex fixes for remaining {final_scan['total_issues']} issues")
        
        # Direct regex replacement for titles (more reliable than AI)
        regex_changes = []
        
        # Fix titles with regex
        if final_scan['titles']:
            original_text = current_text
            current_text = re.sub(r'\bMr\.', 'Mx.', current_text)
            current_text = re.sub(r'\bMrs\.', 'Mx.', current_text)
            current_text = re.sub(r'\bMs\.', 'Mx.', current_text)
            current_text = re.sub(r'\bMiss\b', 'Mx.', current_text)
            
            if current_text != original_text:
                regex_changes.append("REGEX: Fixed all remaining titles (Mr./Mrs./Ms./Miss → Mx.)")
        
        # Fix obvious pronouns with regex (be careful with context)
        if final_scan['he_she']:
            # Only fix standalone he/she at word boundaries
            original_text = current_text
            current_text = re.sub(r'\bhe\b', 'they', current_text)
            current_text = re.sub(r'\bHe\b', 'They', current_text)
            current_text = re.sub(r'\bshe\b', 'they', current_text)
            current_text = re.sub(r'\bShe\b', 'They', current_text)
            
            if current_text != original_text:
                regex_changes.append("REGEX: Fixed remaining he/she pronouns")
        
        if regex_changes:
            all_qc_changes.extend(regex_changes)
            print(f"   ✅ Regex fixed {len(regex_changes)} categories of issues")
    
    # Final verification
    final_scan = scan_for_gendered_language(current_text, transform_type)
    
    if final_scan['total_issues'] == 0:
        print(f"🎯 QC SUCCESS: Achieved 100% transformation!")
    else:
        print(f"⚠️ QC INCOMPLETE: {final_scan['total_issues']} issues remain after all attempts")
        print(f"   Remaining issues: {final_scan}")
    
    return current_text, all_qc_changes

@safe_api_call
@cache_result()
def transform_gender_with_context(text: str, transform_type: str, character_context: str, model: str = "gpt-4") -> Tuple[str, List[str]]:
    """Transform text to use specified gender pronouns and references with character context.
    
    Args:
        text: The text to transform
        transform_type: Type of transformation (feminine, masculine, neutral)
        character_context: Context about characters in the text
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
    
    # Create systematic prompt based on transformation type
    if transform_type == "neutral":
        system_prompt = """
You are a systematic text processor. Transform ALL gendered language to neutral forms.

MANDATORY RULES - Apply to EVERY instance without exception:
- he/He → they/They
- she/She → they/They  
- him/Him → them/Them
- her/Her → them/Them (when object pronoun)
- his/His → their/Their
- himself/Himself → themselves/Themselves
- herself/Herself → themselves/Themselves
- Mr./Mrs./Ms./Miss → Mx.

PROCESS:
1. Scan entire text systematically
2. Find ALL instances of gendered pronouns and titles
3. Replace every single one - no exceptions
4. Maintain original punctuation and structure
5. Return valid JSON with transformed text and changes list

CRITICAL: You will be scored on completeness. Missing even one gendered pronoun is failure.
"""
        user_prompt = f"""
Transform this text to use neutral gender language. Replace ALL gendered pronouns and titles systematically.

Character context for reference:
{character_context}

Text to transform:
{text}

Return JSON with:
{{"text": "transformed text", "changes": ["list of changes made"]}}
"""
    else:
        system_prompt = f"""
You are a systematic text processor. Transform ALL gendered language to {transform_info['name'].lower()} forms.

Apply the transformation rules systematically to every instance.
Maintain original text structure and return valid JSON.
"""
        user_prompt = f"""
{transform_info['description']}.
Make these specific changes:
{chr(10).join(f"{i+1}. Change {change}" for i, change in enumerate(transform_info['changes']))}

Character context:
{character_context}

Text to transform:
{text}

Return JSON with:
{{"text": "transformed text", "changes": ["list of changes made"]}}
"""
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    
    try:
        result = json.loads(response.choices[0].message.content)
        if 'text' not in result or 'changes' not in result:
            raise APIError("API response missing required fields: 'text' and/or 'changes'")
        
        # Automatic QC pass to catch any missed transformations
        qc_text, qc_changes = automatic_qc_pass(result['text'], transform_type, model)
        
        # Combine changes from both passes
        all_changes = result['changes'] + qc_changes
        
        return qc_text, all_changes
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
