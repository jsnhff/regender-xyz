"""Character analysis prompt using flagship-quality approach for maximum accuracy."""

from typing import Dict, Tuple, Optional


def get_character_analysis_prompt(text: str, 
                                 model: Optional[str] = None,
                                 provider: Optional[str] = None) -> Tuple[str, str]:
    """Get character analysis prompt using flagship-quality approach.
    
    We use only the highest quality prompt approach regardless of model,
    as errors in character identification can cascade through the entire
    book transformation and waste significant human proofreading time.
    
    Args:
        text: Text to analyze
        model: Model name (unused)
        provider: Provider name (unused)
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Use flagship approach for all models - quality is paramount
    return _get_flagship_character_prompt(text)


def _get_flagship_character_prompt(text: str) -> Tuple[str, str]:
    """High-quality character analysis prompt for maximum accuracy."""
    system = """You are an expert literary character analysis system. Your task is to identify ALL characters in the provided text with maximum precision and zero errors.

CRITICAL PRINCIPLES:
1. NEVER merge different people (family members are ALWAYS separate characters)
2. Track ALL characters - major, minor, and even briefly mentioned
3. Use pronouns and context to determine gender accurately
4. Preserve narrative relationships and roles
5. Output only valid, parseable JSON"""
    
    user = f"""Analyze this text and extract ALL characters with their properties.

ANALYSIS REQUIREMENTS:

1. CHARACTER IDENTIFICATION
   - Find every person mentioned by name in the text
   - Include characters who are referenced but not present (e.g., "his late father")
   - Track titles (Mr./Mrs./Dr./Lord/Lady/etc.) as part of names
   - Note nicknames and informal references

2. GENDER DETERMINATION
   - Use pronouns (he/him/his = male, she/her/hers = female)
   - Use titles and honorifics (Mr./Sir/Lord = male, Mrs./Ms./Lady = female)
   - Use contextual clues (mother/father, son/daughter, wife/husband)
   - Mark as "unknown" ONLY when no evidence exists

3. CHARACTER SEPARATION RULES
   - Family members are ALWAYS different characters
   - "Harry Potter" and "James Potter" are TWO different people
   - "Mrs. Bennet" and "Elizabeth Bennet" are TWO different people
   - NEVER assume one character is another without explicit text evidence

4. ROLE IDENTIFICATION
   - Describe each character's role or function in the story
   - Note relationships to other characters
   - Include profession, social position, or defining traits

OUTPUT FORMAT (strict JSON):
{{
    "characters": {{
        "Character Full Name": {{
            "name": "Most complete name form found",
            "gender": "male|female|unknown",
            "role": "Brief description of character's role/function",
            "name_variants": ["All", "name", "variations", "found"],
            "relationships": {{
                "Other Character Name": "relationship type (e.g., father, friend, employer)"
            }},
            "context_notes": "Any important context about this character"
        }}
    }},
    "metadata": {{
        "total_characters": <number>,
        "gender_distribution": {{
            "male": <count>,
            "female": <count>,
            "unknown": <count>
        }},
        "confidence_notes": ["Any caveats or uncertainties"]
    }}
}}

EXAMPLE OUTPUT STRUCTURE:
{{
    "characters": {{
        "Elizabeth Bennet": {{
            "name": "Elizabeth Bennet",
            "gender": "female",
            "role": "Second eldest Bennet daughter, protagonist",
            "name_variants": ["Elizabeth", "Lizzy", "Eliza", "Miss Elizabeth Bennet"],
            "relationships": {{
                "Mr. Bennet": "daughter",
                "Jane Bennet": "sister",
                "Mr. Darcy": "love interest"
            }},
            "context_notes": "Often called Lizzy by family"
        }},
        "Mr. Bennet": {{
            "name": "Mr. Bennet",
            "gender": "male",
            "role": "Father of five daughters, country gentleman",
            "name_variants": ["Mr. Bennet"],
            "relationships": {{
                "Elizabeth Bennet": "father",
                "Mrs. Bennet": "husband"
            }},
            "context_notes": "Sarcastic, prefers his library"
        }}
    }}
}}

TEXT TO ANALYZE:
{text}

Remember: Quality is paramount. It's better to list characters separately if unsure than to incorrectly merge them. Output ONLY valid JSON."""

    return system, user