"""Character analysis module for identifying and profiling characters in text."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, NamedTuple
import re
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from pydantic import BaseModel, validator

class Mention(NamedTuple):
    """Represents a single mention of a character in text."""
    start: int  # Start position in text
    end: int    # End position in text
    text: str   # Actual text found
    context: str  # Surrounding sentence or clause
    mention_type: str  # 'name', 'pronoun', or 'possessive'
    
    def to_dict(self) -> dict:
        """Convert mention to dictionary for JSON serialization."""
        return dict(self._asdict())
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Mention':
        """Create Mention from dictionary."""
        return cls(**data)

@dataclass
class Character:
    """Represents a character found in the text."""
    name: str
    gender: Optional[str] = None
    role: Optional[str] = None
    mentions: List[Mention] = field(default_factory=list)
    name_variants: List[str] = field(default_factory=list)
    
    def add_mention(self, start: int, end: int, text: str, full_text: str, mention_type: str = 'name') -> None:
        """Add a mention with its surrounding context."""
        # Extract surrounding context (simplified to use a fixed window)
        context_start = max(0, start - 50)
        context_end = min(len(full_text), end + 50)
        context = full_text[context_start:context_end].strip()
        
        mention = Mention(start, end, text, context, mention_type)
        if mention not in self.mentions:
            # Insert maintaining order by position
            self.mentions.insert(next((i for i, m in enumerate(self.mentions) 
                                    if m.start > start), len(self.mentions)), mention)
    
    def add_variant(self, variant: str) -> None:
        """Add a name variant if it's not already recorded."""
        if variant and variant not in self.name_variants:
            self.name_variants.append(variant)
    
    def to_dict(self) -> dict:
        """Convert character to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'gender': self.gender,
            'role': self.role,
            'mentions': [m.to_dict() for m in self.mentions],
            'name_variants': self.name_variants
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Character':
        """Create Character from dictionary."""
        mentions = [Mention.from_dict(m) for m in data['mentions']]
        return cls(
            name=data['name'],
            gender=data['gender'],
            role=data['role'],
            mentions=mentions,
            name_variants=data['name_variants']
        )

class CharacterData(BaseModel):
    canonical_name: str
    role: str
    gender: str
    name_variants: List[str]
    pronouns: List[str]
    possessives: List[str]

def clean_name(name: str) -> str:
    """Remove leading numbers, periods, and clean up whitespace."""
    return ' '.join(name.strip().split())

def get_gpt_response(prompt: str, client: OpenAI) -> str:
    """Get response from GPT model."""
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error getting GPT response: {e}")
        return ""

def find_characters(text: str, client: OpenAI) -> Dict[str, Character]:
    """Find characters in the text using AI."""
    prompt = f"""Analyze this text and identify all characters. For each character, provide:
1. Their canonical name (most complete form used)
2. Their primary role in the narrative and relationship to other characters
3. Their gender (if mentioned or clearly implied)
4. All variations of their name found in the text (titles, first name only, etc.)
5. All pronouns and possessive forms used for this character

Requirements:
- Be specific about roles (e.g., "Lucy's mother" rather than just "parent")
- Include relationship context (e.g., "Professor at the same university as Lucy")
- Note gender markers in the text (pronouns used, gender-specific terms)
- List ALL name variations exactly as they appear
- Include pronouns (he/she/they) and possessives (his/her/their)

Format the response as JSON with this structure:
{{
    "characters": [
        {{
            "canonical_name": "full name with title if available",
            "role": "specific role and relationships",
            "gender": "gender with brief evidence",
            "name_variants": ["all", "name", "variations", "found"],
            "pronouns": ["list", "of", "pronouns", "used"],
            "possessives": ["list", "of", "possessive", "forms"]
        }}
    ]
}}

Here's the text:

{text}"""

    response = get_gpt_response(prompt, client)
    
    try:
        data = json.loads(response)
        characters = {}
        
        for char_data in data["characters"]:
            char_data = CharacterData(**char_data)
            # Create character with canonical name
            main_name = clean_name(char_data.canonical_name)
            character = Character(
                name=main_name,
                role=char_data.role,
                gender=char_data.gender
            )
            
            # Process all references to this character
            for variant in set(char_data.name_variants) | {main_name}:
                variant = clean_name(variant)
                if variant:
                    character.add_variant(variant)
                    pos = 0
                    while (pos := text.find(variant, pos)) != -1:
                        character.add_mention(pos, pos + len(variant), variant, text, 'name')
                        pos += len(variant)
            
            # Track pronouns and possessives
            for mention_type, words in [
                ('pronoun', char_data.pronouns),
                ('possessive', char_data.possessives)
            ]:
                for word in words:
                    pos = 0
                    while (pos := text.find(word, pos)) != -1:
                        character.add_mention(pos, pos + len(word), word, text, mention_type)
                        pos += len(word)
            
            characters[main_name] = character
            
        return characters
    except Exception as e:
        print(f"Error processing characters: {e}")
        return {}

def save_character_analysis(characters: Dict[str, Character], output_file: str) -> None:
    """Save character analysis results to a JSON file."""
    data = {
        'characters': {name: char.to_dict() for name, char in characters.items()},
        'metadata': {
            'version': '1.0',
            'timestamp': datetime.now().isoformat(),
            'character_count': len(characters)
        }
    }
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
