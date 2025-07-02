#!/usr/bin/env python3
"""
AI Learning Loop Module
Standalone quality control system that can be integrated into any transformation pipeline.
"""

import json
import re
from typing import List, Dict, Tuple, Any
from api_client import UnifiedLLMClient


def scan_for_gendered_language(text: str, transform_type: str) -> Dict[str, Any]:
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
    
    return {'total_issues': 0}


def ai_comprehensive_scan(text: str, transform_type: str, model: str = "gpt-4o-mini", provider: str = "openai") -> List[Dict[str, str]]:
    """Use AI to comprehensively find ALL gendered language with context understanding."""
    
    client = UnifiedLLMClient(provider)
    
    # Define what we're looking for based on transformation type
    if transform_type == "neutral":
        target_description = "gender-neutral language (they/them/their, Mx., neutral terms)"
        examples = "he→they, she→they, his→their, Mr./Mrs.→Mx., king→monarch, uncle→parent's sibling"
    elif transform_type == "feminine":
        target_description = "feminine language (she/her/her, Ms., feminine terms)"
        examples = "he→she, him→her, his→her, Mr.→Ms., king→queen, uncle→aunt"
    elif transform_type == "masculine":
        target_description = "masculine language (he/him/his, Mr., masculine terms)"
        examples = "she→he, her→him, her→his, Mrs./Ms.→Mr., queen→king, aunt→uncle"
    
    ai_prompt = f"""You are an expert at finding gendered language that needs transformation.

TASK: Scan this text and find ALL instances of gendered language that should be transformed to {target_description}.

LOOK FOR:
1. Pronouns: he, she, him, her, his, himself, herself
2. Titles: Mr., Mrs., Ms., Miss, Sir, Madam
3. Family terms: father, mother, brother, sister, uncle, aunt, son, daughter, etc.
4. Royal/Noble: king, queen, prince, princess, duke, duchess, lord, lady
5. Social terms: man, woman, boy, girl, gentleman, lady
6. Occupational: businessman/woman, actor/actress, waiter/waitress, etc.
7. Relationship: husband, wife, boyfriend, girlfriend
8. ANY other gendered language

IMPORTANT CONTEXT RULES:
- Skip proper nouns (like "Uncle Sam", "King Street", character names)
- Skip quoted titles of books/movies
- Consider context - don't change things that would sound awkward
- Focus on narrative pronouns and descriptive terms

EXAMPLES: {examples}

For each gendered term you find, provide:
- The exact word/phrase that needs changing
- What it should become
- 20-30 characters of surrounding context
- The position in text (approximate)

TEXT TO SCAN:
{text}

Return JSON in this EXACT format:
{{
  "found_terms": [
    {{
      "error": "original word",
      "correction": "replacement word",
      "context": "surrounding text",
      "type": "pronoun|title|family|royal|social|occupational",
      "confidence": "high"
    }}
  ]
}}

BE THOROUGH - find EVERY gendered term that should be transformed.
"""

    try:
        # Note: Grok doesn't support response_format parameter
        kwargs = {
            "messages": [
                {"role": "system", "content": "You are an expert at context-aware gendered language detection."},
                {"role": "user", "content": ai_prompt}
            ],
            "model": model,
            "temperature": 0.1
        }
        
        # Only add response_format for OpenAI
        if provider == "openai":
            kwargs["response_format"] = {"type": "json_object"}
            
        response = client.complete(**kwargs)
        
        result = json.loads(response.content)
        
        # Handle different possible response formats
        if isinstance(result, list):
            return result
        elif 'errors' in result:
            return result['errors']
        elif 'gendered_terms' in result:
            return result['gendered_terms']
        elif 'found_terms' in result:
            return result['found_terms']
        else:
            return []
            
    except Exception as e:
        print(f"AI scan failed: {e}")
        return []


def regex_fallback_scan(text: str, transform_type: str) -> List[Dict[str, str]]:
    """Regex fallback for basic patterns AI might miss."""
    
    errors = []
    
    # Basic pronouns and titles that should ALWAYS be caught
    if transform_type == "neutral":
        patterns = [
            (r'\b(he|He)\b', 'they'),
            (r'\b(she|She)\b', 'they'), 
            (r'\b(him|Him)\b', 'them'),
            (r'\b(his|His)\b', 'their'),
            (r'\b(Mr\.)\s*', 'Mx. '),
            (r'\b(Mrs\.)\s*', 'Mx. '),
            (r'\b(Ms\.)\s*', 'Mx. ')
        ]
    elif transform_type == "feminine":
        patterns = [
            (r'\b(he|He)\b', 'she'),
            (r'\b(him|Him)\b', 'her'),
            (r'\b(his|His)\b', 'her'),
            (r'\b(Mr\.)\s*', 'Ms. ')
        ]
    elif transform_type == "masculine":
        patterns = [
            (r'\b(she|She)\b', 'he'),
            (r'\b(her|Her)\b', 'him'),  # Simplified - AI handles possessive vs object
            (r'\b(Mrs\.)\s*', 'Mr. '),
            (r'\b(Ms\.)\s*', 'Mr. ')
        ]
    else:
        patterns = []
    
    for pattern, replacement in patterns:
        for match in re.finditer(pattern, text):
            # Preserve original capitalization
            original = match.group()
            if original[0].isupper() and len(replacement) > 0:
                corrected = replacement[0].upper() + replacement[1:]
            else:
                corrected = replacement
            
            errors.append({
                'error': original,
                'correction': corrected,
                'context': text[max(0, match.start()-20):match.end()+20],
                'position': match.start(),
                'type': 'regex_fallback',
                'confidence': 'high'
            })
    
    return errors


def find_specific_errors(text: str, transform_type: str, use_ai: bool = True, model: str = "gpt-4o-mini", provider: str = "openai") -> List[Dict[str, str]]:
    """
    Find gendered language errors using AI-first approach with regex fallback.
    
    Args:
        text: Text to scan
        transform_type: Type of transformation
        use_ai: Whether to use AI scan (True) or just regex (False)
    """
    
    if use_ai:
        # AI-first: Comprehensive, context-aware detection
        print(f"   🧠 AI scanning for gendered language...")
        ai_errors = ai_comprehensive_scan(text, transform_type, model, provider)
        
        if ai_errors:
            print(f"   ✅ AI found {len(ai_errors)} gendered terms")
            return ai_errors
        else:
            print(f"   ⚠️ AI scan failed or found nothing, falling back to regex...")
    
    # Regex fallback: Basic but reliable patterns
    print(f"   🔧 Using regex fallback scan...")
    regex_errors = regex_fallback_scan(text, transform_type)
    print(f"   ✅ Regex found {len(regex_errors)} basic patterns")
    
    return regex_errors


def apply_learning_pass(text: str, transform_type: str, errors: List[Dict[str, str]], 
                       iteration: int, model: str = "gpt-4o-mini", provider: str = "openai") -> Tuple[str, List[str]]:
    """Apply a single AI learning pass to fix specific errors."""
    
    client = UnifiedLLMClient(provider)
    
    # Group errors by type
    pronoun_errors = [e for e in errors if e['type'] == 'pronoun']
    title_errors = [e for e in errors if e['type'] == 'title']
    
    # Create learning-focused prompt with specific examples
    error_examples = []
    
    if pronoun_errors:
        error_examples.append("PRONOUN ERRORS YOU MISSED:")
        for i, error in enumerate(pronoun_errors[:8], 1):
            error_examples.append(f"{i}. '{error['error']}' should be '{error['correction']}' in: ...{error['context']}...")
    
    if title_errors:
        error_examples.append("\nTITLE ERRORS YOU MISSED:")
        for i, error in enumerate(title_errors[:5], 1):
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
    
    learning_prompt = f"""You are learning from your mistakes. In your previous {transform_type} transformation, you missed {len(errors)} gendered language instances.

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

{text}

Return JSON with:
{{"text": "corrected text with ALL errors fixed", "changes": ["specific corrections made with reasoning"]}}
"""
    
    try:
        # Build kwargs based on provider
        kwargs = {
            "messages": [
                {"role": "system", "content": f"You are learning from {len(errors)} specific errors. Pass {iteration}: Be more intelligent about language patterns."},
                {"role": "user", "content": learning_prompt}
            ],
            "model": model,
            "temperature": 0.1
        }
        
        # Only add response_format for OpenAI
        if provider == "openai":
            kwargs["response_format"] = {"type": "json_object"}
            
        response = client.complete(**kwargs)
        
        result = json.loads(response.content)
        if 'text' in result and 'changes' in result:
            return result['text'], [f"Learning{iteration}: {change}" for change in result['changes']]
        else:
            return text, []
            
    except Exception as e:
        print(f"      ⚠️ Learning pass {iteration} failed: {e}")
        # Return original text and empty changes on failure
        return text, []


def apply_regex_fallback(text: str, transform_type: str, remaining_issues: Dict[str, Any]) -> Tuple[str, List[str]]:
    """Apply regex fallback for stubborn issues."""
    
    regex_changes = []
    current_text = text
    
    if transform_type == "neutral" and remaining_issues['total_issues'] > 0:
        # Fix titles with regex
        if remaining_issues['titles']:
            original_text = current_text
            current_text = re.sub(r'\bMr\.', 'Mx.', current_text)
            current_text = re.sub(r'\bMrs\.', 'Mx.', current_text)
            current_text = re.sub(r'\bMs\.', 'Mx.', current_text)
            current_text = re.sub(r'\bMiss\b', 'Mx.', current_text)
            
            if current_text != original_text:
                regex_changes.append("REGEX: Fixed all remaining titles (Mr./Mrs./Ms./Miss → Mx.)")
        
        # Fix obvious pronouns with regex
        if remaining_issues['he_she']:
            original_text = current_text
            current_text = re.sub(r'\bhe\b', 'they', current_text)
            current_text = re.sub(r'\bHe\b', 'They', current_text)
            current_text = re.sub(r'\bshe\b', 'they', current_text)
            current_text = re.sub(r'\bShe\b', 'They', current_text)
            
            if current_text != original_text:
                regex_changes.append("REGEX: Fixed remaining he/she pronouns")
    
    return current_text, regex_changes


def quality_control_loop(text: str, transform_type: str, model: str = "gpt-4o-mini", 
                        provider: str = "openai", max_iterations: int = 5, verbose: bool = True) -> Tuple[str, List[str]]:
    """
    Run complete quality control loop until 100% transformation achieved.
    
    Args:
        text: Text from initial transformation pass
        transform_type: Type of transformation (neutral, feminine, masculine)
        model: AI model to use for learning passes
        max_iterations: Maximum learning iterations
        verbose: Print progress messages
        
    Returns:
        Tuple of (cleaned_text, list_of_additional_changes)
    """
    
    current_text = text
    all_qc_changes = []
    iteration = 0
    
    if verbose:
        print("🧠 Starting AI learning loop until 100% transformation...")
    
    while iteration < max_iterations:
        iteration += 1
        
        # Find specific errors with context
        errors = find_specific_errors(current_text, transform_type, True, model, provider)
        
        if not errors:
            if verbose:
                print(f"   ✅ LEARNING COMPLETE: 100% transformation achieved after {iteration-1} QC passes")
            break
            
        if verbose:
            print(f"   🧠 Learning Pass {iteration}: Found {len(errors)} specific errors to teach AI")
        
        # Apply learning pass
        learned_text, qc_changes = apply_learning_pass(current_text, transform_type, errors, iteration, model, provider)
        
        if qc_changes:
            current_text = learned_text
            all_qc_changes.extend(qc_changes)
            if verbose:
                print(f"      🎯 AI learned and fixed {len(qc_changes)} issues")
        else:
            if verbose:
                print(f"      ❌ Learning pass {iteration} returned no changes")
            # Don't break - continue trying until max iterations
            continue
    
    # Final verification - check if we still have issues
    final_errors = find_specific_errors(current_text, transform_type, True, model, provider)
    
    if verbose:
        if not final_errors:
            print(f"🎯 QC SUCCESS: Achieved 100% transformation!")
        else:
            print(f"⚠️ QC INCOMPLETE: {len(final_errors)} issues remain after {iteration} attempts")
            print("   Remaining issues:")
            for i, error in enumerate(final_errors[:5], 1):
                print(f"     {i}. '{error['error']}' → '{error['correction']}' in: ...{error.get('context', 'N/A')}...")
            if len(final_errors) > 5:
                print(f"     ... and {len(final_errors) - 5} more")
    
    return current_text, all_qc_changes