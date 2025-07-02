"""Character analysis prompt templates adapted to model capabilities."""

from typing import Dict, Tuple, Optional
# Import moved inside function to avoid circular import


def get_character_analysis_prompt(text: str, 
                                 model: Optional[str] = None,
                                 provider: Optional[str] = None) -> Tuple[str, str]:
    """Get character analysis prompts based on model capabilities.
    
    Args:
        text: Text to analyze
        model: Model name
        provider: Provider name
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Get model configuration
    from book_transform.model_config_loader import get_verified_model_config
    config = get_verified_model_config(model, provider)
    
    # Default to basic tier if no config found
    tier = config.tier if config else "basic"
    
    # Adjust text length based on tier
    text_limits = {
        "basic": 2000,
        "standard": 5000,
        "advanced": 10000,
        "flagship": 20000
    }
    max_text = text_limits.get(tier, 2000)
    analysis_text = text[:max_text] if len(text) > max_text else text
    
    # Get prompts based on tier
    if tier == "basic":
        return _get_basic_character_prompt(analysis_text)
    elif tier == "standard":
        return _get_standard_character_prompt(analysis_text)
    elif tier == "advanced":
        return _get_advanced_character_prompt(analysis_text)
    else:  # flagship
        return _get_flagship_character_prompt(analysis_text)


def _get_basic_character_prompt(text: str) -> Tuple[str, str]:
    """Simple prompt for basic models."""
    system = "You are a character analysis assistant. Identify characters and output JSON."
    
    user = f"""Find the main characters in this text.

For each character provide:
- name: their name
- gender: male or female
- role: brief description

Output as JSON:
{{
    "characters": {{
        "Name": {{
            "name": "Name",
            "gender": "male or female",
            "role": "description"
        }}
    }}
}}

Text: {text}

Output JSON only."""

    return system, user


def _get_standard_character_prompt(text: str) -> Tuple[str, str]:
    """Improved prompt to avoid character merging issues."""
    system = """You are a precise literary character analyst. Your task is to identify individual characters from the text and determine their properties. 

CRITICAL RULES:
1. Each character is a SEPARATE entity - never merge different people together
2. Family members are DIFFERENT characters (e.g., Harry Potter and Lily Potter are two different people)
3. If unsure whether two names refer to the same person, list them separately
4. Focus on clear, unambiguous character identification"""
    
    user = f"""Analyze this text and identify all individual characters.

INSTRUCTIONS:
1. List each unique person as a separate character
2. For each character, determine:
   - Their most complete name
   - Gender from pronouns/titles (he/him=male, she/her=female, otherwise=unknown)
   - Their role or description from the text
   - Any alternate names ONLY if explicitly stated as the same person

IMPORTANT RULES:
- DO NOT merge family members (parents and children are different people)
- DO NOT assume relationships unless explicitly stated
- DO NOT combine characters unless the text explicitly says they're the same person
- If you see "X's mother" or "X's father", that's a DIFFERENT character than X
- Each person gets their own entry

OUTPUT FORMAT (strict JSON):
{{
    "characters": {{
        "Full Character Name": {{
            "name": "Most complete name form",
            "gender": "male|female|unknown",
            "role": "Brief description from text",
            "name_variants": ["only", "explicit", "alternates"],
            "mentions": []
        }}
    }}
}}

Example of CORRECT separation:
- "Harry Potter" - the boy protagonist (separate entry)
- "Lily Potter" - Harry's mother (separate entry)  
- "James Potter" - Harry's father (separate entry)

TEXT TO ANALYZE:
{text}

Remember: When in doubt, keep characters SEPARATE. Never merge different people."""

    return system, user


def _get_advanced_character_prompt(text: str) -> Tuple[str, str]:
    """Optimized prompt for Grok and other advanced models."""
    system = """You are an expert character identification system. Extract all characters with maximum precision.

Your approach:
1. Scan for all proper names (capitalized names referring to people)
2. Identify gender from grammatical clues
3. Extract roles and relationships from context
4. Keep each person as a distinct entity
5. Never merge different individuals"""
    
    user = f"""Perform comprehensive character analysis on the provided text.

Requirements:
1. Identify ALL characters (major, minor, and mentioned)
2. Track their gender through pronouns and context
3. Determine their role and relationships
4. Note all name variations and titles

For each character, provide:
- name: Full canonical name
- gender: Determined from pronouns/context (male/female/unknown)
- role: Their function in the narrative
- name_variants: All variations, nicknames, titles
- first_appearance: Brief note about when they appear

JSON Schema:
{{
    "characters": {{
        "Full Character Name": {{
            "name": "string - full name",
            "gender": "male|female|unknown",
            "role": "string - narrative role",
            "name_variants": ["array", "of", "variations"],
            "first_appearance": "string - context of first mention",
            "mentions": []
        }}
    }},
    "metadata": {{
        "total_characters": "number",
        "confidence": "high|medium|low"
    }}
}}

Analyze this text:
{text}

Output valid JSON matching the schema. Be thorough but accurate."""

    return system, user


def _get_flagship_character_prompt(text: str) -> Tuple[str, str]:
    """Advanced prompt with position tracking for flagship models."""
    system = """You are a precision literary analysis system with advanced NLP capabilities.
Your task requires exact character identification with position tracking.
Follow all instructions precisely and output valid JSON."""
    
    user = f"""Execute comprehensive character entity recognition and analysis.

REQUIRED TASKS:
1. Character Identification
   - Extract ALL character entities (proper names)
   - Include titles, nicknames, and references
   
2. Gender Analysis
   - Determine gender from pronouns (he/she/they)
   - Use contextual clues and titles (Mr./Mrs./Ms.)
   - Mark as "unknown" if unclear
   
3. Position Tracking (CRITICAL)
   - Record exact character positions for each mention
   - start: 0-based index where mention begins
   - end: 0-based index where mention ends
   - Verify: text[start:end] == mention_text
   
4. Context Extraction
   - Include the complete sentence containing each mention
   - Classify mention type: name|pronoun|possessive|title

OUTPUT SCHEMA (strict JSON):
{{
    "characters": {{
        "Character Full Name": {{
            "name": "string",
            "gender": "male|female|unknown",
            "role": "string - narrative function",
            "mentions": [
                {{
                    "start": 0,
                    "end": 0,
                    "text": "exact text",
                    "context": "full sentence",
                    "mention_type": "name|pronoun|possessive|title"
                }}
            ],
            "name_variants": ["array of all variations"],
            "relationships": {{"other_character": "relationship type"}}
        }}
    }},
    "metadata": {{
        "total_characters": 0,
        "total_mentions": 0,
        "analysis_confidence": "high|medium|low",
        "processing_notes": ["any relevant notes"]
    }}
}}

TEXT FOR ANALYSIS:
{text}

IMPORTANT: Output ONLY valid JSON. Ensure all positions are accurate."""

    return system, user