"""
Improved prompts for LLM character analysis.

These prompts are designed to be explicit about JSON structure
and prevent common parsing issues.
"""


EXTRACTION_PROMPT_TEMPLATE = """Extract ALL characters from this text. Return ONLY valid JSON, no markdown or explanation.

Find ALL: protagonists, main characters, family members (all siblings!), supporting roles, minor characters, unnamed roles.
Include: all name variations, nicknames, titles, descriptive names.
CRITICAL: Don't merge family members with same surname - they are different people!

Required JSON structure:
{{
  "characters": [
    {{
      "name": "most complete/formal name",
      "gender": "male/female/neutral/unknown",
      "pronouns": "he/she/they/etc",
      "description": "brief character role",
      "aliases": ["ALL nicknames", "variations", "what others call them"],
      "titles": ["Mr/Ms/Dr/Lord/etc"]
    }}
  ]
}}

Rules:
- Must be valid JSON object with "characters" array
- All fields required (empty arrays/strings if unknown)
- No markdown blocks (no ```json)
- Extract EVERY character mentioned

Text to analyze:
{text}"""


MERGE_PROMPT_TEMPLATE = """Analyze if these characters are the same person. Return ONLY valid JSON.

Characters to analyze:
{characters}

Required JSON:
{{
  "is_same_person": true or false,
  "canonical_name": "most complete/formal name",
  "gender": "male/female/neutral/unknown",
  "pronouns": "combined pronouns",
  "description": "merged description",
  "aliases": ["ALL unique names from ALL entries combined"]
}}

Rules:
- is_same_person must be boolean (not string)
- If same person: merge ALL aliases from all entries
- If different: use first character's info
- No markdown or text outside JSON"""


GROUP_ANALYSIS_PROMPT_TEMPLATE = """Analyze which characters in this list refer to the same person.

CRITICAL: Return ONLY valid JSON with no additional text.

Characters:
{characters}

Required JSON structure:
{{
  "merge_groups": [
    [0, 5, 7],  // Indices of characters that are the same person
    [1, 3],     // Another group of same person
    // Single indices don't need to be included
  ],
  "explanations": {{
    "0,5,7": "All refer to Huckleberry Finn",
    "1,3": "Both refer to Tom Sawyer"
  }}
}}

Rules:
1. Return a JSON object with "merge_groups" and "explanations" keys
2. merge_groups contains arrays of indices that should be merged
3. Only include groups with 2+ characters
4. Indices are 0-based from the input list
5. Do NOT include markdown or explanatory text

Return the JSON object now:"""


TRANSFORM_BATCH_PROMPT_TEMPLATE = """Gender transformation expert. Transform {batch_size} paragraphs.

{rules}

{character_info}

Transform exactly {batch_size} paragraphs. Preserve all other aspects.
Return transformed paragraphs separated by blank lines.
NO explanations or metadata."""


TRANSFORM_SIMPLE_PROMPT_TEMPLATE = """You are a precise text transformer. Apply gender swapping rules to the text.

TRANSFORMATION TYPE: {transform_type}

{rules}

{character_instructions}

Return ONLY the transformed text with NO explanations or metadata."""
