"""Improved character analysis prompts that reduce ambiguity and merging errors."""

def get_improved_character_prompt(text: str, chunk_info: str = "") -> tuple[str, str]:
    """Get an improved character analysis prompt that minimizes confusion."""
    
    system_prompt = """You are a precise literary character analyst. Your task is to identify individual characters from the text and determine their properties. 

CRITICAL RULES:
1. Each character is a SEPARATE entity - never merge different people together
2. Family members are DIFFERENT characters (e.g., Harry Potter and Lily Potter are two different people)
3. If unsure whether two names refer to the same person, list them separately
4. Focus on clear, unambiguous character identification"""

    user_prompt = f"""Analyze this text and identify all individual characters.
{chunk_info}

INSTRUCTIONS:
1. List each unique person as a separate character
2. For each character, determine:
   - Their most complete name
   - Gender from pronouns/titles (he/him=male, she/her=female, otherwise=unknown)
   - Their role or description from the text
   - Any alternate names or nicknames ONLY if explicitly stated

IMPORTANT RULES:
- DO NOT merge family members (parents and children are different people)
- DO NOT assume relationships unless explicitly stated
- DO NOT combine characters unless the text explicitly says they're the same person
- If you see "X's mother" or "X's father", that's a DIFFERENT character than X

OUTPUT FORMAT (strict JSON):
{{
    "characters": {{
        "Full Character Name": {{
            "gender": "male|female|unknown",
            "role": "exact description from text",
            "alternate_names": ["only", "explicit", "alternates"],
            "confidence": "high|medium|low"
        }}
    }}
}}

Example of CORRECT separation:
- "Harry Potter" - the protagonist (separate entry)
- "Lily Potter" - Harry's mother (separate entry)
- "James Potter" - Harry's father (separate entry)

Text to analyze:
{text}

Remember: When in doubt, keep characters SEPARATE. Never merge different people."""

    return system_prompt, user_prompt


def get_grok_optimized_prompt(text: str, chunk_num: int = 0, total_chunks: int = 0) -> tuple[str, str]:
    """Prompt optimized for Grok's capabilities."""
    
    chunk_info = ""
    if chunk_num > 0:
        chunk_info = f"\n[Analyzing chunk {chunk_num} of {total_chunks}]\n"
    
    system_prompt = """You are an expert character identification system. Extract all characters with maximum precision.

Your approach:
1. Scan for all proper names (capitalized names referring to people)
2. Identify gender from grammatical clues
3. Extract roles and relationships from context
4. Keep each person as a distinct entity"""

    user_prompt = f"""Extract all characters from this text with their properties.
{chunk_info}
For each character provide:
- Full name (most complete version found)
- Gender (based on pronouns: he/him=male, she/her=female, they/them or unclear=unknown)
- Role/description (from the text)
- Any explicitly mentioned alternate names

CRITICAL: Each person is a separate character. Never merge different individuals.

Special attention:
- Family members are different people (Harry Potter ≠ James Potter ≠ Lily Potter)
- Titles indicate different people (Mr. Potter might be James, Mrs. Potter might be Lily)
- "X's [relation]" means a different person than X

Output as clean JSON:
{{
    "characters": {{
        "Character Full Name": {{
            "gender": "male|female|unknown",
            "role": "description from text",
            "alternate_names": ["explicit alternates only"]
        }}
    }}
}}

Text:
{text}

Extract characters - keep them distinct:"""

    return system_prompt, user_prompt


def create_consolidation_rules():
    """Create rules for safe character consolidation."""
    return {
        "rules": [
            {
                "name": "exact_match",
                "description": "Only merge if names are exactly the same",
                "test": lambda n1, n2: n1.lower() == n2.lower()
            },
            {
                "name": "explicit_alternate",
                "description": "Merge if one is listed as alternate name of the other",
                "test": lambda n1, n2, alts1, alts2: n1 in alts2 or n2 in alts1
            },
            {
                "name": "nickname_match",
                "description": "Merge if one is clearly a nickname (must have same last name)",
                "test": lambda n1, n2: (
                    len(n1.split()) > 1 and len(n2.split()) > 1 and
                    n1.split()[-1] == n2.split()[-1] and
                    (n1.split()[0] in n2 or n2.split()[0] in n1)
                )
            }
        ],
        "forbidden_merges": [
            # Never merge if roles indicate different generations
            lambda r1, r2: not (
                ("father" in r1 and "son" in r2) or
                ("mother" in r1 and "daughter" in r2) or
                ("parent" in r1 and "child" in r2) or
                any(rel in r1 and rel in r2 for rel in ["uncle", "aunt", "nephew", "niece"])
            )
        ]
    }


def validate_character_merge(char1: dict, char2: dict, name1: str, name2: str) -> bool:
    """Validate if two characters can be safely merged."""
    # Never merge different genders (unless one is unknown)
    if (char1.get('gender') != 'unknown' and 
        char2.get('gender') != 'unknown' and 
        char1.get('gender') != char2.get('gender')):
        return False
    
    # Never merge if roles are incompatible
    role1 = char1.get('role', '').lower()
    role2 = char2.get('role', '').lower()
    
    # Check for family relationships that indicate different people
    family_terms = [
        ("mother", "son"), ("mother", "daughter"),
        ("father", "son"), ("father", "daughter"),
        ("parent", "child"), ("uncle", "nephew"),
        ("aunt", "niece"), ("grandfather", "grandson"),
        ("grandmother", "granddaughter")
    ]
    
    for term1, term2 in family_terms:
        if (term1 in role1 and term2 in role2) or (term2 in role1 and term1 in role2):
            return False
    
    # Don't merge if one is described as older/younger than the other
    if ("older" in role1 and "younger" in role2) or ("younger" in role1 and "older" in role2):
        return False
    
    # Don't merge if they have conflicting titles
    if ("mr." in role1.lower() and "mrs." in role2.lower()) or \
       ("mrs." in role1.lower() and "mr." in role2.lower()):
        return False
    
    return True