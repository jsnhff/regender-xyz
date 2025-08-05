"""
Quality control module for gender transformation.
Integrated from the standalone review_loop.py for unified transformation pipeline.
"""

import json
import re
from typing import List, Dict, Tuple, Any, Optional
from datetime import datetime
from api_client import UnifiedLLMClient


def scan_for_gendered_language(text: str, transform_type: str) -> Dict[str, Any]:
    """Scan text for remaining gendered language patterns."""
    
    if transform_type == "all_female":
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
    
    elif transform_type == "all_male":
        she_matches = re.findall(r'\b(she|She)\b', text)
        her_matches = re.findall(r'\b(her|Her)\b', text)
        female_titles = re.findall(r'\b(Mrs\.|Ms\.|Miss)\s+', text)
        
        total_issues = len(she_matches + her_matches + female_titles)
        
        return {
            'total_issues': total_issues,
            'he_she': she_matches,
            'him_her': her_matches,
            'his_her': [],
            'titles': female_titles
        }
    
    elif transform_type == "gender_swap":
        # For gender swap, we need to check context to ensure swaps were made
        # This is more complex and might need the character mapping
        return {
            'total_issues': 0,
            'message': 'Gender swap validation requires character context'
        }
    
    return {'total_issues': 0}


def find_specific_errors(text: str, transform_type: str, use_ai: bool = True, 
                        provider: str = 'grok', verbose: bool = False) -> List[Dict[str, str]]:
    """Find specific gendered language errors using pattern matching and optionally AI."""
    
    errors = []
    
    # First do pattern-based detection
    scan_results = scan_for_gendered_language(text, transform_type)
    
    if scan_results['total_issues'] == 0:
        return errors
    
    if not use_ai:
        # Just return pattern matches
        for match in scan_results.get('he_she', []):
            errors.append({
                'error': match,
                'correction': 'she' if transform_type == 'all_female' else 'he',
                'type': 'pronoun'
            })
        return errors
    
    # Use AI for more sophisticated error detection
    client = UnifiedLLMClient(provider=provider)
    
    # Take a sample of the text for AI analysis
    sample_size = min(len(text), 10000)
    text_sample = text[:sample_size]
    
    prompt = f"""Analyze this text excerpt for gender language that doesn't match the {transform_type} transformation.

Text excerpt:
{text_sample}

Target transformation: {transform_type}

Find specific instances where gendered language (pronouns, titles, etc.) doesn't match the target.
For each error found, provide:
1. The exact text that's wrong
2. What it should be changed to
3. Brief context (a few words before/after)

Format as JSON array:
[{{"error": "he", "correction": "she", "context": "...when he arrived..."}}]

Only include actual errors, not correct usage."""

    try:
        response = client.complete(
            messages=[
                {"role": "system", "content": "You are a precise editor focused on gender language consistency."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        # Parse response
        result = json.loads(response.content)
        if isinstance(result, dict) and 'errors' in result:
            errors.extend(result['errors'])
        elif isinstance(result, list):
            errors.extend(result)
            
    except Exception as e:
        if verbose:
            print(f"AI error detection failed: {e}")
    
    return errors


def apply_corrections(text: str, corrections: List[Dict[str, str]], verbose: bool = False) -> Tuple[str, List[str]]:
    """Apply a list of corrections to the text."""
    
    changes_made = []
    corrected_text = text
    
    for correction in corrections:
        old_text = correction.get('error', '')
        new_text = correction.get('correction', '')
        context = correction.get('context', '')
        
        if not old_text or not new_text:
            continue
            
        # Try to find and replace based on context if provided
        if context:
            # Find the context in the text
            if context in corrected_text:
                # Replace within context
                new_context = context.replace(old_text, new_text)
                if new_context != context:
                    corrected_text = corrected_text.replace(context, new_context)
                    changes_made.append(f"Changed '{old_text}' to '{new_text}' in context: {context[:50]}...")
        else:
            # Simple word boundary replacement
            pattern = r'\b' + re.escape(old_text) + r'\b'
            new_corrected = re.sub(pattern, new_text, corrected_text)
            if new_corrected != corrected_text:
                count = len(re.findall(pattern, corrected_text))
                corrected_text = new_corrected
                changes_made.append(f"Changed '{old_text}' to '{new_text}' ({count} occurrences)")
    
    return corrected_text, changes_made


def quality_control_loop(text: str, transform_type: str, model: Optional[str] = None,
                        provider: str = 'grok', max_iterations: int = 3,
                        verbose: bool = True) -> Tuple[str, List[str]]:
    """
    Run quality control loop to fix remaining gender language issues.
    
    Returns:
        Tuple of (cleaned_text, list_of_changes_made)
    """
    
    all_changes = []
    current_text = text
    
    for iteration in range(max_iterations):
        if verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Quality Control Iteration {iteration + 1}/{max_iterations}")
        
        # Find errors
        errors = find_specific_errors(current_text, transform_type, use_ai=True, provider=provider)
        
        if not errors:
            if verbose:
                print("  ✓ No gender language issues found")
            break
            
        if verbose:
            print(f"  Found {len(errors)} potential issues")
        
        # Apply corrections
        current_text, changes = apply_corrections(current_text, errors, verbose=verbose)
        
        if not changes:
            if verbose:
                print("  No corrections could be applied")
            break
            
        all_changes.extend(changes)
        
        if verbose:
            print(f"  Applied {len(changes)} corrections")
    
    return current_text, all_changes


def validate_transformation(original_text: str, transformed_text: str, 
                          transform_type: str, character_context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Validate the quality of a transformation.
    
    Returns a report with metrics and issues found.
    """
    
    # Basic scan
    issues = scan_for_gendered_language(transformed_text, transform_type)
    
    # Calculate metrics
    original_words = len(original_text.split())
    transformed_words = len(transformed_text.split())
    
    report = {
        'transform_type': transform_type,
        'total_issues': issues['total_issues'],
        'issue_details': issues,
        'word_count_change': transformed_words - original_words,
        'word_count_ratio': transformed_words / original_words if original_words > 0 else 0,
        'quality_score': max(0, 100 - (issues['total_issues'] * 2))  # Simple scoring
    }
    
    # Character consistency check if context provided
    if character_context:
        report['character_consistency'] = check_character_consistency(
            transformed_text, character_context, transform_type
        )
    
    return report


def check_character_consistency(text: str, character_context: Dict, transform_type: str) -> Dict[str, Any]:
    """Check if character genders are consistently transformed."""
    
    consistency_report = {
        'consistent': True,
        'issues': []
    }
    
    # This would check each character's mentions against their expected gender
    # For now, returning placeholder
    
    return consistency_report