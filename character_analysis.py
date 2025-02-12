"""Character analysis module for identifying and profiling characters in text."""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
import re
import os
import json
from openai import OpenAI

client = OpenAI()

@dataclass
class Character:
    """Represents a character found in the text."""
    name: str
    gender: Optional[str] = None
    role: Optional[str] = None
    mentions: List[int] = field(default_factory=list)  # List of positions where character is mentioned
    name_variants: List[str] = field(default_factory=list)  # Different forms of the name found in text
    
    def add_mention(self, position: int) -> None:
        """Add a mention position if it's not already recorded."""
        if position not in self.mentions:
            self.mentions.append(position)
            self.mentions.sort()  # Keep mentions in order of appearance
    
    def add_variant(self, variant: str) -> None:
        """Add a name variant if it's not already recorded."""
        if variant and variant not in self.name_variants:
            self.name_variants.append(variant)

def clean_name(name: str) -> str:
    """Remove leading numbers, periods, and clean up whitespace."""
    name = re.sub(r'^[\d\.\s]+', '', name.strip())
    return re.sub(r'\s+', ' ', name)  # Normalize whitespace

def get_gpt_response(prompt: str, model: str = "gpt-4", temperature: float = 0.7) -> str:
    """Get response from GPT model.
    
    Args:
        prompt: Input prompt for GPT
        model: Model to use
        temperature: Response randomness
        
    Returns:
        Model's response text
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting GPT response: {e}")
        return ""

def find_characters(text: str) -> Dict[str, Character]:
    """Find characters names in the text using AI.
    
    Args:
        text: The input text to analyze
        
    Returns:
        Dictionary mapping character names to Character objects
    """
    # Create a prompt that asks GPT to identify characters
    prompt = f"""Analyze this text and identify all characters. For each character, provide:
1. Their canonical name (most complete form used)
2. Their primary role in the narrative and relationship to other characters
3. Their gender (if mentioned or clearly implied)
4. All variations of their name found in the text (titles, first name only, etc.)

Requirements:
- Be specific about roles (e.g., "Lucy's mother" rather than just "parent")
- Include relationship context (e.g., "Professor at the same university as Lucy")
- Note gender markers in the text (pronouns used, gender-specific terms)
- List ALL name variations exactly as they appear

Format the response as JSON with this structure:
{{
    "characters": [
        {{
            "canonical_name": "full name with title if available",
            "role": "specific role and relationships",
            "gender": "gender with brief evidence",
            "name_variants": ["all", "name", "variations", "found"]
        }}
    ]
}}

Here's the text:

{text}"""

    # Get GPT's analysis
    response = get_gpt_response(prompt)
    
    # Parse the JSON response
    try:
        data = json.loads(response)
        characters = {}
        
        for char_data in data["characters"]:
            # Create character object with canonical name
            main_name = clean_name(char_data["canonical_name"])
            character = Character(
                name=main_name,
                role=char_data.get("role"),
                gender=char_data.get("gender")
            )
            
            # Add all name variations
            variants = set(char_data.get("name_variants", []))
            variants.add(main_name)  # Include canonical name in variants
            for variant in variants:
                variant = clean_name(variant)
                if variant:
                    character.add_variant(variant)
                    # Find all occurrences of this variant
                    start = 0
                    while True:
                        pos = text.find(variant, start)
                        if pos == -1:
                            break
                        character.add_mention(pos)
                        start = pos + len(variant)  # Start after this mention
            
            characters[main_name] = character
            
        return characters
    except json.JSONDecodeError:
        print("Error: Could not parse GPT response as JSON")
        return {}
    except Exception as e:
        print(f"Error processing characters: {e}")
        return {}
