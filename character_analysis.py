"""Character analysis module for identifying and profiling characters in text."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, NamedTuple, Tuple
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
        # Get sentence bounds
        context_start, context_end = find_sentence_bounds(full_text, start)
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

def find_sentence_bounds(text: str, pos: int, max_context: int = 200) -> Tuple[int, int]:
    """Find the start and end of sentence(s) containing position pos.
    
    Args:
        text: The full text to search in
        pos: The position to find context for
        max_context: Maximum characters of context (default: 200)
    
    Returns:
        Tuple of (start, end) positions that capture the context
    """
    # Common sentence endings and honorifics
    end_markers = {'.', '!', '?'}
    # Pre-compile honorific checks for efficiency
    honorific_endings = '|'.join(h + '.' for h in ['mr', 'mrs', 'ms', 'dr', 'prof', 'rev', 'sr', 'jr'])
    honorific_pattern = re.compile(f'({honorific_endings})$', re.IGNORECASE)
    
    def is_sentence_end(pos: int) -> bool:
        """Check if position is a true sentence end."""
        if pos >= len(text) or text[pos] not in end_markers:
            return False
            
        # Look back for honorific
        prev_word_end = text.rfind(' ', max(0, pos-10), pos) + 1
        if honorific_pattern.search(text[prev_word_end:pos+1]):
            return False
        
        # Must be followed by space/quote and capital, or end of text
        after = pos + 1
        while after < len(text) and text[after] in ' \t\n"\'':
            after += 1
        return after >= len(text) or text[after].isupper()
    
    # Look backwards for sentence start
    start = pos
    while start > 0:
        # Stop at previous sentence end or paragraph break
        if is_sentence_end(start - 1) or \
           (start > 1 and text[start-2:start] == '\n\n'):
            break
        start -= 1
    
    # Clean up start (skip whitespace and quotes)
    while start < len(text) and text[start] in ' \t\n"\'':
        start += 1
    
    # Look forwards for sentence end
    end = pos
    while end < len(text):
        # Check context size
        if end - start >= max_context:
            # Complete dialogue if we're in the middle of one
            quote_count = text[start:end].count('"')
            if quote_count % 2 == 1:
                next_quote = text.find('"', end)
                if next_quote != -1 and next_quote - start < max_context + 50:
                    end = next_quote + 1
            break
            
        # Stop at sentence end
        if is_sentence_end(end):
            end += 1
            # Include one more sentence if it's short
            next_end = end
            while next_end < len(text) and text[next_end] in ' \t\n"\'':
                next_end += 1
            next_sentence_end = next_end
            while next_sentence_end < len(text):
                if is_sentence_end(next_sentence_end):
                    if next_sentence_end - end < 50:  # Short enough to include
                        end = next_sentence_end + 1
                    break
                next_sentence_end += 1
            break
        
        end += 1
    
    # Clean up end (include closing punctuation but trim trailing space)
    while end > start and text[end-1] in ' \t\n':
        end -= 1
    
    return start, end

def add_mention(character: Character, start: int, end: int, text: str, full_text: str, mention_type: str = 'name') -> None:
    """Add a mention with its surrounding context using sentence boundaries."""
    # Get sentence bounds
    context_start, context_end = find_sentence_bounds(full_text, start)
    context = full_text[context_start:context_end].strip()
    
    mention = Mention(start, end, text, context, mention_type)
    if mention not in character.mentions:
        # Insert maintaining order by position
        character.mentions.insert(next((i for i, m in enumerate(character.mentions) 
                                if m.start > start), len(character.mentions)), mention)

class CharacterData(BaseModel):
    canonical_name: str
    role: Optional[str] = None
    gender: Optional[str] = None
    name_variants: List[str] = []
    pronouns: List[str] = []
    possessives: List[str] = []

class GPTResponse(BaseModel):
    characters: List[CharacterData]

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
        data = GPTResponse.parse_raw(response)
        characters = {}
        
        # First pass: Create characters and process name mentions
        for char_data in data.characters:
            main_name = clean_name(char_data.canonical_name)
            character = Character(
                name=main_name,
                role=char_data.role,
                gender=char_data.gender
            )
            
            # Process name variations first
            for variant in set(char_data.name_variants) | {main_name}:
                variant = clean_name(variant)
                if variant:
                    character.add_variant(variant)
                    pos = 0
                    while (pos := text.find(variant, pos)) != -1:
                        character.add_mention(pos, pos + len(variant), variant, text, 'name')
                        pos += len(variant)
            
            characters[main_name] = character

        # Second pass: Process pronouns with proximity-based attribution
        for char_data in data.characters:
            character = characters[clean_name(char_data.canonical_name)]
            
            # Group pronouns by gender
            male_pronouns = {'he', 'him', 'his', 'himself'}
            female_pronouns = {'she', 'her', 'hers', 'herself'}
            neutral_pronouns = {'they', 'them', 'their', 'theirs', 'themselves'}
            
            # Determine character's pronoun set based on gender
            if character.gender and 'male' in character.gender.lower():
                valid_pronouns = male_pronouns
            elif character.gender and 'female' in character.gender.lower():
                valid_pronouns = female_pronouns
            else:
                valid_pronouns = neutral_pronouns
            
            # Process pronouns and possessives together
            all_refs = set(char_data.pronouns) | set(char_data.possessives)
            for word in all_refs:
                if word.lower() not in valid_pronouns:
                    continue
                    
                pos = 0
                while (pos := text.find(word, pos)) != -1:
                    # Find nearest preceding name mention
                    nearest_char = None
                    min_distance = float('inf')
                    
                    for char in characters.values():
                        # Only consider characters of matching gender
                        if not char.gender or not character.gender or \
                           ('male' in char.gender.lower()) != ('male' in character.gender.lower()):
                            continue
                            
                        # Find the most recent name mention before this pronoun
                        for mention in char.mentions:
                            if mention.mention_type == 'name' and mention.end <= pos:
                                distance = pos - mention.end
                                if distance < min_distance:
                                    min_distance = distance
                                    nearest_char = char
                    
                    # Only attribute pronoun if this character is the nearest match
                    # and within reasonable distance (200 chars)
                    if nearest_char == character and min_distance < 200:
                        mention_type = 'possessive' if word.lower() in {'his', 'her', 'their', 'hers', 'theirs'} else 'pronoun'
                        character.add_mention(pos, pos + len(word), word, text, mention_type)
                    
                    pos += len(word)
            
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
