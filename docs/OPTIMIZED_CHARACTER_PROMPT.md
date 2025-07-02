# Optimized Character Extraction Prompt for Mistral-Small-24B

This prompt is specifically optimized for the Mistral-Small-3.2-24B model's capabilities, leveraging its 128k context window while maintaining clarity and precision.

## System Prompt
```
You are a literary character analyst specializing in character identification and gender analysis. Your task is to extract all characters from the provided text and determine their gender based on pronouns, titles, and contextual clues.
```

## User Prompt Template
```
Analyze this text and identify ALL characters mentioned, including their gender and role.

INSTRUCTIONS:
1. Find every character name (proper nouns referring to people)
2. Determine gender from:
   - Pronouns (he/she/they)
   - Titles (Mr./Mrs./Ms./Lord/Lady)
   - Context clues
   - Mark as "unknown" if unclear
3. Identify all name variations (nicknames, titles, full/partial names)
4. Note their primary role or occupation if mentioned

OUTPUT FORMAT (strict JSON):
{
    "characters": {
        "Full Character Name": {
            "name": "Most complete name form",
            "gender": "male|female|unknown",
            "role": "Brief description of role/occupation",
            "name_variants": ["All", "name", "variations", "found"],
            "mentions": []
        }
    }
}

EXAMPLES:
- "Harry Potter" with variants ["Harry", "Mr. Potter", "The Boy Who Lived"]
- "Hermione Granger" with variants ["Hermione", "Miss Granger", "'Mione"]

IMPORTANT RULES:
- Include EVERY character, even if mentioned only once
- Use the longest/most formal name as the main key
- List ALL variations in name_variants
- Be consistent with gender across the same character
- Output ONLY valid JSON, no explanations

TEXT TO ANALYZE:
[INSERT TEXT HERE]

Output the JSON character analysis:
```

## Why This Prompt Works Well for Mistral-Small-24B

1. **Clear Structure**: The prompt has explicit sections that Mistral models handle well
2. **Examples**: Concrete examples help the model understand the expected format
3. **Strict JSON**: Clear formatting requirements with examples
4. **Balanced Detail**: Not too simple (like basic tier) but not overly complex
5. **Focus on Essentials**: Skips position tracking which can confuse mid-tier models

## Usage Tips

1. **Text Length**: With 128k context, you can analyze up to ~90k tokens of text in one go
2. **Two-Phase Approach**: Still use fast_scan first to focus the analysis
3. **Temperature**: Keep at 0 for consistent results
4. **Validation**: Always validate the JSON output as Mistral models sometimes add explanations

## Alternative Compact Version

For even better results with Mistral-Small, here's a more compact version:

```
Extract all characters from this text. For each character provide their full name, gender (male/female/unknown based on pronouns/titles), role, and any name variations.

Output as JSON:
{
    "characters": {
        "Character Name": {
            "name": "string",
            "gender": "male|female|unknown", 
            "role": "string",
            "name_variants": ["array"],
            "mentions": []
        }
    }
}

Analyze this text:
[TEXT]

JSON output:
```

## Integration with Your System

To use this optimized prompt in your code:

```python
# In book_characters/prompts.py, update the standard prompt:

def _get_standard_character_prompt(text: str) -> Tuple[str, str]:
    """Optimized prompt for Mistral-Small and similar standard models."""
    system = """You are a literary character analyst specializing in character identification and gender analysis. Your task is to extract all characters from the provided text and determine their gender based on pronouns, titles, and contextual clues."""
    
    user = f"""Analyze this text and identify ALL characters mentioned, including their gender and role.

INSTRUCTIONS:
1. Find every character name (proper nouns referring to people)
2. Determine gender from:
   - Pronouns (he/she/they)
   - Titles (Mr./Mrs./Ms./Lord/Lady)
   - Context clues
   - Mark as "unknown" if unclear
3. Identify all name variations (nicknames, titles, full/partial names)
4. Note their primary role or occupation if mentioned

OUTPUT FORMAT (strict JSON):
{{
    "characters": {{
        "Full Character Name": {{
            "name": "Most complete name form",
            "gender": "male|female|unknown",
            "role": "Brief description of role/occupation",
            "name_variants": ["All", "name", "variations", "found"],
            "mentions": []
        }}
    }}
}}

EXAMPLES:
- "Harry Potter" with variants ["Harry", "Mr. Potter", "The Boy Who Lived"]
- "Hermione Granger" with variants ["Hermione", "Miss Granger", "'Mione"]

IMPORTANT RULES:
- Include EVERY character, even if mentioned only once
- Use the longest/most formal name as the main key
- List ALL variations in name_variants
- Be consistent with gender across the same character
- Output ONLY valid JSON, no explanations

TEXT TO ANALYZE:
{text}

Output the JSON character analysis:"""

    return system, user
```

## Testing the Prompt

Test with a sample text:
```bash
# Using your local Mistral-Small model
export LLM_PROVIDER=mlx
python regender_book_cli.py analyze-characters books/json/sample_book.json \
    --output characters.json \
    --model mistral-small
```

## Expected Output Quality

With this optimized prompt, Mistral-Small-24B should:
- Identify 90%+ of characters correctly
- Determine gender accurately when pronouns/titles are present
- Group name variants effectively
- Produce valid JSON in most cases
- Complete analysis in 1-2 passes for most books

## Troubleshooting

If the model struggles:
1. Reduce text length per chunk
2. Use the compact version of the prompt
3. Add more examples specific to your text style
4. Consider using the fast_scan results as hints