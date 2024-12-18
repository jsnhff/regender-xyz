"""Text processing and chunking functionality."""

from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Tuple, Set, Dict
import re

from config.constants import DEFAULT_CHUNK_SIZE, CHUNK_OVERLAP
from utils.api_client import get_gpt_response

class TextProcessor:
    def __init__(self, max_tokens: int = DEFAULT_CHUNK_SIZE):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_tokens,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", "!", "?", " "],
            keep_separator=True
        )

    def chunk_text(self, text: str) -> Tuple[List[str], List[Dict]]:
        """Split text into chunks and track character context."""
        chunks = self.text_splitter.split_text(text)
        character_contexts = self._build_character_contexts(chunks)
        return chunks, character_contexts

    def _build_character_contexts(self, chunks: List[str]) -> List[Dict]:
        """Build character context information for each chunk."""
        character_contexts = []
        all_characters = set()

        for i, chunk in enumerate(chunks):
            characters_in_chunk = self._extract_characters(chunk)
            all_characters.update(characters_in_chunk)
            
            character_contexts.append({
                'chunk_index': i,
                'characters': characters_in_chunk,
                'all_characters_so_far': set(all_characters)
            })
        
        return character_contexts

    def _extract_characters(self, chunk: str) -> Set[str]:
        """Extract character mentions from a chunk with improved filtering."""
        roles_info = self._detect_roles(chunk)
        characters = set()
        
        if roles_info:
            for line in roles_info.splitlines():
                parts = line.split(" - ")
                if len(parts) >= 1:
                    character = self._clean_name(parts[0])
                    # Filter out likely non-characters
                    if self._is_valid_character(character):
                        characters.add(character)
        
        return characters

    @staticmethod
    def _detect_roles(text: str) -> str:
        """Detect character roles using GPT with improved prompt."""
        prompt = (
            "Identify only the actual characters (people, named entities) in this text. "
            "Ignore general nouns, concepts, or unnamed entities. "
            "For each real character, provide their role and apparent gender.\n\n"
            f"Text: {text}\n\n"
            "Format: Character - Role - Gender\n"
            "Only include actual characters with proper names or clear character roles. "
            "Exclude abstract concepts, general references, or background elements."
        )
        return get_gpt_response(prompt)

    @staticmethod
    def _is_valid_character(name: str) -> bool:
        """
        Check if a name is likely to be a valid character.
        Returns True if the name passes validation rules.
        """
        # Skip if too short
        if len(name) < 2:
            return False
            
        # Skip common non-character phrases
        invalid_patterns = [
            'the ', 'a ', 'an ', 'this ', 'that ',
            'voice', 'sound', 'noise', 'feeling',
            'morning', 'evening', 'night', 'day'
        ]
        
        name_lower = name.lower()
        
        # Check against invalid patterns
        if any(pattern in name_lower for pattern in invalid_patterns):
            return False
            
        # Require at least one uppercase letter (proper names usually start with capitals)
        if not any(c.isupper() for c in name):
            return False
            
        return True

    @staticmethod
    def _clean_name(name: str) -> str:
        """Clean and normalize a character name."""
        return re.sub(r'^\d+\.\s*', '', name).strip()

    def regender_text(self, chunk, chunk_characters):
        """Process a chunk of text with character gender information."""
        # Format character info for GPT
        gender_guidelines = []
        
        # Handle chunk_characters as a list
        if isinstance(chunk_characters, list):
            for char_info in chunk_characters:
                if 'characters' in char_info:
                    for character in char_info['characters']:
                        gender_guidelines.append(f"{character}: Unknown")
        
        # Prepare prompt for GPT
        prompt = (
            "Regender the following text:\n\n"
            "Character genders:\n"
            f"{chr(10).join(gender_guidelines)}\n\n"
            "Text to process:\n"
            f"{chunk}"
        )

        return get_gpt_response(prompt)