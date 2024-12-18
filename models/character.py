"""Character model and related operations."""

from dataclasses import dataclass
from typing import Dict, Optional
import json

from config.constants import GENDER_CATEGORIES

@dataclass
class Character:
    original_name: str
    original_role: str
    original_gender: str
    updated_name: Optional[str] = None
    updated_role: Optional[str] = None
    updated_gender: Optional[str] = None
    gender_category: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert character to dictionary for JSON serialization."""
        return {
            "Original_Name": self.original_name,
            "Original_Role": self.original_role,
            "Original_Gender": self.original_gender,
            "Updated_Name": self.updated_name or self.original_name,
            "Updated_Role": self.updated_role or self.original_role,
            "Updated_Gender": self.updated_gender or self.original_gender,
            "Gender_Category": self.gender_category
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Character':
        """Create character instance from dictionary."""
        return cls(
            original_name=data["Original_Name"],
            original_role=data["Original_Role"],
            original_gender=data["Original_Gender"],
            updated_name=data.get("Updated_Name"),
            updated_role=data.get("Updated_Role"),
            updated_gender=data.get("Updated_Gender"),
            gender_category=data.get("Gender_Category")
        )

class CharacterManager:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.characters = {}

    def load_characters(self) -> None:
        """Load characters from JSON file."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.characters = {
                    char_data["Original_Name"]: Character.from_dict(char_data)
                    for char_data in data.get("Characters", [])
                }
        except FileNotFoundError:
            self.characters = {}

    def save_characters(self) -> None:
        """Save characters to JSON file."""
        data = {
            "Characters": [char.to_dict() for char in self.characters.values()]
        }
        with open(self.file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def update_character(self, character: Character) -> None:
        """Update or add a character."""
        self.characters[character.original_name] = character
        self.save_characters()

    def get_character(self, name: str) -> Optional[Character]:
        """Get character by name."""
        return self.characters.get(name)