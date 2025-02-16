"""Character analysis module for identifying and profiling characters in text."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, NamedTuple, Tuple, Set
import re
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI
from pydantic import BaseModel, validator
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Mention(NamedTuple):
    """Represents a single mention of a character in text."""
    start: int  # Start position in text
    end: int    # End position in text
    text: str   # Actual text found
    context: str  # Surrounding sentence or clause
    mention_type: str  # 'name', 'pronoun', or 'possessive'
    confidence: float = 1.0  # Confidence score (0-1)
    validated: bool = False  # Whether this mention has been validated by AI
    
    def to_dict(self) -> dict:
        """Convert mention to dictionary for JSON serialization."""
        return dict(self._asdict())
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Mention':
        """Create Mention from dictionary."""
        return cls(**data)
    
    def get_validation_prompt(self, character_name: str) -> str:
        """Generate a prompt to validate this mention."""
        return f"""Given this text excerpt:

"{self.context}"

Question: Does the {self.mention_type} "{self.text}" refer to the character "{character_name}"?

Requirements:
- Consider the surrounding context carefully
- Check if any other characters could be the referent
- Look for clear indicators of who is being referenced
- Consider paragraph and dialogue boundaries

Answer with ONLY "yes" or "no"."""

@dataclass
class Character:
    """Represents a character found in the text."""
    name: str
    gender: Optional[str] = None
    role: Optional[str] = None
    mentions: List[Mention] = field(default_factory=list)
    name_variants: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)
    
    def add_mention(self, start: int, end: int, text: str, full_text: str, mention_type: str = 'name', 
                    confidence: float = 1.0, validated: bool = False) -> None:
        """Add a mention with its surrounding context."""
        # Get sentence bounds
        context_start, context_end = find_sentence_bounds(full_text, start)
        context = full_text[context_start:context_end].strip()
        
        mention = Mention(start, end, text, context, mention_type, confidence, validated)
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
            'name_variants': self.name_variants,
            'relationships': self.relationships
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
            name_variants=data['name_variants'],
            relationships=data.get('relationships', {})
        )

def find_sentence_bounds(text: str, pos: int, max_context: int = 200) -> Tuple[int, int]:
    """Find the start and end of sentence(s) containing position pos."""
    # Find sentence start
    start = pos
    while start > 0 and not text[start-1] in {'.', '!', '?', '\n\n'}:
        start -= 1
        if pos - start > max_context:
            break
    
    # Find sentence end
    end = pos
    while end < len(text) and not text[end] in {'.', '!', '?', '\n\n'}:
        end += 1
        if end - pos > max_context:
            break
    
    # Adjust bounds to avoid partial words
    while start < pos and not text[start].isspace():
        start += 1
    while end > pos and not text[end-1].isspace():
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
    """Clean a character name."""
    if not name:
        return ''
    # Remove extra whitespace
    name = ' '.join(name.split())
    # Remove trailing punctuation
    name = name.rstrip('.,!?:;')
    return name

def is_valid_variant(canonical: str, variant: str) -> bool:
    """Check if a name variant is valid for a canonical name."""
    if not variant or not canonical:
        return False
        
    # Clean both names
    canonical = clean_name(canonical).lower()
    variant = clean_name(variant).lower()
    
    # Must be different
    if canonical == variant:
        return False
        
    # Extract title and name parts
    canonical_parts = canonical.split()
    variant_parts = variant.split()
    
    # Get titles (Mr., Mrs., Miss, etc.)
    canonical_title = canonical_parts[0] if canonical_parts and canonical_parts[0].endswith('.') else ''
    variant_title = variant_parts[0] if variant_parts and variant_parts[0].endswith('.') else ''
    
    # If titles exist, they must match or variant must have no title
    if canonical_title and variant_title and canonical_title != variant_title:
        return False
    
    # Get name parts (excluding titles)
    canonical_name = ' '.join(canonical_parts[1:] if canonical_title else canonical_parts)
    variant_name = ' '.join(variant_parts[1:] if variant_title else variant_parts)
    
    # Variant must be part of canonical name or vice versa
    return canonical_name in variant_name or variant_name in canonical_name

def get_gpt_response(prompt: str, client: OpenAI) -> str:
    """Get response from GPT model."""
    logger.info(f"Making API call with prompt length: {len(prompt)}")
    try:
        response = client.chat.completions.create(
            model="gpt-4-0125-preview",  # Using latest model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
            timeout=30  # Add timeout to prevent hanging
        )
        result = response.choices[0].message.content
        logger.info(f"Got response of length: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"Error getting GPT response: {e}")
        return ""

def get_character_context(text: str, name: str, client: OpenAI) -> Tuple[str, str, List[str], Set[str]]:
    """Get detailed context for a character including role, gender, and name variants."""
    context_prompt = f"""Analyze this character: {name}

Text excerpt:
{text[:2000]}...

IMPORTANT: Your response must be EXACTLY ONE LINE using this format:
role|gender|variant1,variant2,variant3|pronoun1,pronoun2,pronoun3

Rules:
1. Role must be a brief description (e.g. "wealthy landowner", "mother of five daughters")
2. Gender must be "male", "female", or "unknown"
3. Variants must include the full name and any variations used in text
4. Pronouns must be the actual pronouns used (e.g. "he,him,his" or "she,her,hers")

Example response (ONE LINE ONLY):
wealthy landowner and friend of Mr. Bingley|male|Mr. Darcy,Darcy,Fitzwilliam Darcy|he,him,his

DO NOT include any other text or explanation. Just the one line in the exact format above."""

    response = get_gpt_response(context_prompt, client)
    try:
        # Only take the last non-empty line to avoid explanatory text
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        if not lines:
            return "", "", [name], set()
            
        last_line = lines[-1]
        if '|' not in last_line:
            return "", "", [name], set()
            
        role, gender, variants, pronouns = last_line.split('|')
        variants = [v.strip() for v in variants.split(',') if v.strip()]
        if not variants:
            variants = [name]
        pronouns = {p.strip().lower() for p in pronouns.split(',') if p.strip()}
        return role.strip(), gender.strip(), variants, pronouns
    except Exception as e:
        logger.error(f"Error parsing character context: {e}")
        return "", "", [name], set()

def get_clean_mention_context(mention: Mention) -> str:
    """Get clean context for a mention, removing metadata and formatting."""
    context = mention.context.strip()
    
    # Skip if context is too short or contains metadata
    if len(context) < 10 or any(x in context.lower() for x in 
        ['copyright', 'project gutenberg', 'illustration', 'chapter']):
        return ""
    
    # Clean up the context
    context = re.sub(r'\s+', ' ', context)  # Normalize whitespace
    context = re.sub(r'\[.*?\]', '', context)  # Remove bracketed content
    context = re.sub(r'\d+\s*$', '', context)  # Remove trailing numbers
    
    # Get sentence containing the mention
    mention_pos = context.find(mention.text)
    if mention_pos == -1:
        return ""
        
    # Find sentence boundaries
    start = context.rfind('.', 0, mention_pos)
    end = context.find('.', mention_pos)
    if start == -1:
        start = 0
    if end == -1:
        end = len(context)
    
    sentence = context[start+1:end].strip()
    return sentence

def get_initial_character_analysis(text: str, client: OpenAI) -> Dict[str, Dict]:
    """Get initial AI analysis of all characters in the text.
    
    Returns a dict mapping character names to their details:
    {
        "Mr. Bennet": {
            "role": "father of five daughters",
            "gender": "male",
            "variants": ["Mr. Bennet", "Mr Bennet", "Bennet"],
            "family_name": "Bennet",
            "relationships": {"Mrs. Bennet": "wife", "Elizabeth": "daughter"},
            "pronouns": ["he", "him", "his"]
        }
    }
    """
    # Split text into ~2000 char chunks for analysis
    chunk_size = 2000
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    
    characters = {}
    for i, chunk in enumerate(chunks):
        prompt = f"""Analyze this text excerpt ({i+1}/{len(chunks)}) and identify all characters.
For each character provide their details in a JSON array. Include ONLY characters who are directly mentioned or take action.

Required format:
{{
  "characters": [
    {{
      "name": "full name with title",
      "role": "brief description",
      "gender": "male/female/unknown",
      "variants": ["name1", "name2"],
      "family_name": "surname if any",
      "relationships": {{"character": "relationship"}},
      "pronouns": ["pronoun1", "pronoun2"]
    }}
  ]
}}

Example response:
{{
  "characters": [
    {{
      "name": "Mr. Darcy",
      "role": "wealthy landowner and friend of Mr. Bingley",
      "gender": "male",
      "variants": ["Mr. Darcy", "Darcy", "Fitzwilliam Darcy"],
      "family_name": "Darcy",
      "relationships": {{"Elizabeth Bennet": "love interest", "Mr. Bingley": "friend"}},
      "pronouns": ["he", "him", "his"]
    }}
  ]
}}

Text excerpt:
{chunk}

Respond with ONLY the JSON, no other text."""

        response = get_gpt_response(prompt, client)
        try:
            # Parse full JSON response
            data = json.loads(response)
            char_list = data.get('characters', [])
            
            # Merge character data
            for char in char_list:
                name = char['name']
                if name not in characters:
                    characters[name] = char
                else:
                    # Merge variants and relationships
                    characters[name]['variants'].extend(v for v in char['variants'] 
                                                     if v not in characters[name]['variants'])
                    characters[name]['relationships'].update(char.get('relationships', {}))
                    
        except Exception as e:
            logger.error(f"Error parsing character data: {e}")
            logger.error(f"Response was: {response}")
            continue
            
    return characters

def find_pronouns_near_name(text: str, name_pos: int, pronoun: str, 
                         char_relationships: Dict[str, str] = None,
                         all_characters: Dict[str, 'Character'] = None) -> List[Tuple[int, float]]:
    """Find pronouns near a name mention with distance and relationship-based confidence scoring."""
    max_distance = 200  # Max chars to look for pronouns
    results = []
    
    # Search before and after name mention
    start = max(0, name_pos - max_distance)
    end = min(len(text), name_pos + max_distance)
    search_text = text[start:end]
    context = text[max(0, start-50):min(len(text), end+50)]  # Extra context for dialog
    
    pos = 0
    while True:
        pos = search_text.find(pronoun, pos)
        if pos == -1:
            break
            
        # Get absolute position
        abs_pos = start + pos
        
        # Calculate distance from name
        distance = abs(abs_pos - name_pos)
        
        # Base confidence from distance
        if distance < 50:
            confidence = 0.9  # Very close
        elif distance < 100:
            confidence = 0.7  # Medium distance
        elif distance < 150:
            confidence = 0.5  # Far
        else:
            confidence = 0.3  # Very far
            
        # Boost confidence for relationships
        if char_relationships and all_characters:
            # Check if there's a related character mentioned within 100 chars
            context_start = max(0, pos - 100)
            context_end = min(len(search_text), pos + 100)
            local_context = search_text[context_start:context_end].lower()
            
            for rel_name, rel_type in char_relationships.items():
                if rel_name in all_characters:
                    rel_char = all_characters[rel_name]
                    for variant in rel_char.name_variants:
                        if variant.lower() in local_context:
                            confidence = min(1.0, confidence + 0.1)
                            break
        
        # Boost confidence for dialog attribution
        dialog_patterns = [
            ('"', '" said'),
            ('"', '" replied'),
            ('"', '" cried'),
            ('"', '" returned'),
        ]
        
        for start_mark, end_mark in dialog_patterns:
            # Look for dialog before pronoun
            dialog_start = search_text.rfind(start_mark, 0, pos)
            if dialog_start != -1:
                dialog_end = search_text.find(end_mark, dialog_start, pos)
                if dialog_end != -1 and dialog_end - dialog_start < 200:
                    confidence = min(1.0, confidence + 0.2)
                    break
            
        # Add position if it's a standalone pronoun
        if (pos == 0 or not search_text[pos-1].isalpha()) and \
           (pos + len(pronoun) >= len(search_text) or not search_text[pos + len(pronoun)].isalpha()):
            results.append((abs_pos, confidence))
            
        pos += len(pronoun)
        
    return results

def process_pronouns(char: Character, text: str, content_start: int,
                    pronouns: List[str], used_positions: Set[int],
                    client: OpenAI, all_characters: Dict[str, Character] = None):
    """Process pronouns for a character with relationship and dialog boosting."""
    pronoun_count = 0
    max_pronouns_per_name = 3
    
    # Get character relationships
    relationships = {}
    if 'relationships' in char.__dict__:
        relationships = char.relationships
    
    # Start with name mentions and look for nearby pronouns
    for mention in char.mentions:
        if mention.mention_type != 'name':
            continue
            
        pronoun_count_this_name = 0
        for pronoun in pronouns:
            # Find pronouns near this name mention with relationship context
            nearby_pronouns = find_pronouns_near_name(
                text,
                mention.start - content_start,
                pronoun,
                relationships,
                all_characters
            )
            
            # Sort by confidence and take top N
            nearby_pronouns.sort(key=lambda x: x[1], reverse=True)
            nearby_pronouns = nearby_pronouns[:max_pronouns_per_name]
            
            # Process found pronouns
            for pos, confidence in nearby_pronouns:
                if pronoun_count_this_name >= max_pronouns_per_name:
                    break
                    
                # Skip if position is already used
                if pos in used_positions:
                    continue
                    
                # Only validate very ambiguous mentions
                if confidence < 0.7:
                    test_mention = Mention(pos + content_start,
                                        pos + content_start + len(pronoun),
                                        text[pos + content_start:pos + content_start + len(pronoun)],
                                        text[pos + content_start-100:pos + content_start+100],
                                        'possessive' if pronoun in {'his', 'her', 'hers'} else 'pronoun',
                                        confidence)
                    is_valid, new_confidence = validate_mention(test_mention, char, client)
                    if not is_valid:
                        continue
                    confidence = new_confidence
                    
                char.add_mention(pos + content_start,
                               pos + content_start + len(pronoun),
                               text[pos + content_start:pos + content_start + len(pronoun)],
                               text,
                               'possessive' if pronoun in {'his', 'her', 'hers'} else 'pronoun',
                               confidence, confidence >= 0.7)
                used_positions.add(pos)
                pronoun_count += 1
                pronoun_count_this_name += 1
                
                if pronoun_count_this_name >= max_pronouns_per_name:
                    break
                    
    return pronoun_count

def find_characters(text: str, client: OpenAI) -> Dict[str, Character]:
    """Find characters in the text using AI."""
    logger.info(f"\nAnalyzing text of length: {len(text)}")
    
    # Skip metadata section at start of file
    content_start = text.find("Chapter I")
    if content_start == -1:
        content_start = 0
    text_content = text[content_start:]
    
    # Get initial AI analysis of characters
    logger.info("Getting initial character analysis...")
    char_knowledge = get_initial_character_analysis(text_content, client)
    logger.info(f"Found {len(char_knowledge)} characters in initial analysis")
    
    characters: Dict[str, Character] = {}
    used_positions: Set[int] = set()
    
    # Process each character
    for name, details in char_knowledge.items():
        char = Character(
            name=name,
            role=details.get('role', ''),
            gender=details.get('gender', ''),
            mentions=[],
            name_variants=details.get('variants', [name]),
            relationships=details.get('relationships', {})
        )
        
        logger.info(f"\nProcessing character: {name}")
        logger.info(f"Role: {char.role}")
        logger.info(f"Gender: {char.gender}")
        logger.info(f"Variants: {char.name_variants}")
        logger.info(f"Pronouns: {details.get('pronouns', set())}")
        
        # Process name mentions first
        mention_count = 0
        for variant in char.name_variants:
            if not variant:
                continue
            pos = 0
            while True:
                pos = text_content.find(variant, pos)
                if pos == -1:
                    break
                    
                # Skip if position is already used
                overlap = False
                for used_pos in used_positions:
                    if pos <= used_pos < pos + len(variant):
                        overlap = True
                        break
                
                if not overlap:
                    global_pos = pos + content_start
                    char.add_mention(global_pos, global_pos + len(variant),
                                   text[global_pos:global_pos + len(variant)],
                                   text, 'name', 1.0, True)
                    used_positions.add(pos)
                    mention_count += 1
                
                pos += len(variant)
        
        logger.info(f"Found {mention_count} name mentions")
        
        # Process pronouns if gender is known
        if char.gender and details.get('pronouns'):
            pronoun_count = process_pronouns(char, text_content, content_start,
                                          details['pronouns'], used_positions, client, characters)
            logger.info(f"Found {pronoun_count} pronoun mentions")
        
        # Sort mentions by confidence for better first mention selection
        char.mentions.sort(key=lambda m: (-m.confidence, m.start))
        characters[name] = char
            
    return characters

def find_closest_name_mention(text: str, pos: int, max_distance: int = 200) -> Optional[Tuple[int, int, str]]:
    """Find the closest name mention before the given position."""
    # Look for titles followed by capitalized words
    title_pattern = r'(?:Mr\.|Mrs\.|Miss|Lady|Sir|Colonel)\s+[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*'
    
    # Search backwards from pos
    search_start = max(0, pos - max_distance)
    text_before = text[search_start:pos]
    
    matches = list(re.finditer(title_pattern, text_before))
    if matches:
        # Get the last (closest) match
        match = matches[-1]
        # Adjust positions to account for search_start offset
        start = search_start + match.start()
        end = search_start + match.end()
        return (start, end, text[start:end])
    
    return None

def validate_mention(mention: Mention, character: Character, client: OpenAI) -> Tuple[bool, float]:
    """Validate a mention and return validation status and confidence score."""
    # Name mentions are always valid with high confidence
    if mention.mention_type == 'name':
        return True, 1.0
    
    # Generate base confidence score from proximity
    base_confidence = 0.0
    closest_name = find_closest_name_mention(mention.context, mention.context.find(mention.text))
    if closest_name:
        name_start, name_end, name_text = closest_name
        # Check if name matches character
        if any(variant.lower() in name_text.lower() for variant in character.name_variants):
            # Score based on distance (closer = higher confidence)
            distance = abs(name_start - mention.context.find(mention.text))
            base_confidence = max(0.1, 1.0 - (distance / 200))  # Linear falloff up to 200 chars
    
    # Only validate very ambiguous mentions (0.4-0.6 confidence)
    # This significantly reduces API calls while still catching the most uncertain cases
    if 0.4 <= base_confidence <= 0.6:
        prompt = mention.get_validation_prompt(character.name)
        try:
            response = get_gpt_response(prompt, client).strip().lower()
            is_valid = response == 'yes'
            # Adjust confidence based on AI validation
            confidence = base_confidence
            if is_valid:
                confidence = max(base_confidence, 0.7)  # Boost confidence if AI validates
            else:
                confidence = min(base_confidence, 0.3)  # Lower confidence if AI rejects
            return is_valid, confidence
        except Exception as e:
            logger.error(f"Error validating mention: {e}")
            return True, base_confidence  # Fall back to proximity-based confidence
    
    return True, base_confidence

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
