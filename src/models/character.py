"""
Character Domain Model

This module defines character-related models for gender analysis
and transformation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class Gender(Enum):
    """Gender enumeration."""

    MALE = "male"
    FEMALE = "female"
    NONBINARY = "non-binary"
    UNKNOWN = "unknown"
    NEUTRAL = "neutral"


@dataclass
class Character:
    """Represents a character in a book."""

    name: str
    gender: Gender
    pronouns: dict[str, str]  # e.g., {"subject": "she", "object": "her", "possessive": "her"}
    titles: list[str] = field(default_factory=list)  # e.g., ["Mr.", "Lord"]
    aliases: list[str] = field(default_factory=list)  # Alternative names
    description: Optional[str] = None
    importance: str = "supporting"  # main, supporting, minor
    confidence: float = 1.0  # Confidence in gender identification

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "gender": self.gender.value,
            "pronouns": self.pronouns,
            "titles": self.titles,
            "aliases": self.aliases,
            "description": self.description,
            "importance": self.importance,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        """Create from dictionary representation."""
        # Handle pronouns as either dict or string
        pronouns = data.get("pronouns", {})
        if isinstance(pronouns, str):
            # Convert "she/her/hers" or "she/her" format to dict
            parts = pronouns.split("/") if pronouns else []
            if len(parts) >= 2:
                pronouns = {
                    "subject": parts[0],
                    "object": parts[1],
                    "possessive": parts[2] if len(parts) > 2 else parts[1]
                }
            else:
                pronouns = {}
        elif pronouns is None:
            pronouns = {}
            
        return cls(
            name=data["name"],
            gender=Gender(data.get("gender", "unknown")),
            pronouns=pronouns,
            titles=data.get("titles", []),
            aliases=data.get("aliases", []),
            description=data.get("description"),
            importance=data.get("importance", "supporting"),
            confidence=data.get("confidence", 1.0),
        )

    def get_all_names(self) -> list[str]:
        """Get all names and aliases for this character."""
        return [self.name] + self.aliases

    def get_gendered_terms(self) -> dict[str, str]:
        """
        Get all gendered terms for this character.

        Returns:
            Dictionary mapping term types to values
        """
        terms = {"name": self.name, **self.pronouns}

        if self.titles:
            terms["title"] = self.titles[0]  # Primary title

        # Add gender-specific terms based on gender
        if self.gender == Gender.MALE:
            terms.update(
                {
                    "sibling": "brother",
                    "parent": "father",
                    "child": "son",
                    "spouse": "husband",
                    "formal": "sir",
                    "royalty": "king",
                }
            )
        elif self.gender == Gender.FEMALE:
            terms.update(
                {
                    "sibling": "sister",
                    "parent": "mother",
                    "child": "daughter",
                    "spouse": "wife",
                    "formal": "madam",
                    "royalty": "queen",
                }
            )

        return terms

    def __repr__(self) -> str:
        """String representation."""
        return f"Character(name='{self.name}', gender={self.gender.value}, importance={self.importance})"


@dataclass
class CharacterAnalysis:
    """Results of character analysis for a book."""

    book_id: str  # Hash or identifier of the analyzed book
    characters: list[Character]
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    provider: Optional[str] = None
    model: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "book_id": self.book_id,
            "characters": [c.to_dict() for c in self.characters],
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CharacterAnalysis":
        """Create from dictionary representation."""
        return cls(
            book_id=data["book_id"],
            characters=[Character.from_dict(c) for c in data.get("characters", [])],
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(),
            provider=data.get("provider"),
            model=data.get("model"),
        )

    def get_character(self, name: str) -> Optional[Character]:
        """Get a character by name."""
        for character in self.characters:
            if character.name == name or name in character.aliases:
                return character
        return None

    def get_main_characters(self) -> list[Character]:
        """Get all main characters."""
        return [c for c in self.characters if c.importance == "main"]

    def get_by_gender(self, gender: Gender) -> list[Character]:
        """Get all characters of a specific gender."""
        return [c for c in self.characters if c.gender == gender]

    def create_context_string(self) -> str:
        """
        Create a context string for transformation prompts.

        Returns:
            Formatted string describing all characters
        """
        lines = []

        # Group by importance
        main_chars = [c for c in self.characters if c.importance == "main"]
        supporting_chars = [c for c in self.characters if c.importance == "supporting"]
        minor_chars = [c for c in self.characters if c.importance == "minor"]

        if main_chars:
            lines.append("Main Characters:")
            for char in main_chars:
                pronouns = (
                    f"{char.pronouns.get('subject', 'they')}/{char.pronouns.get('object', 'them')}"
                )
                lines.append(f"  - {char.name} ({char.gender.value}, {pronouns})")

        if supporting_chars:
            lines.append("\nSupporting Characters:")
            for char in supporting_chars:
                lines.append(f"  - {char.name} ({char.gender.value})")

        if minor_chars:
            lines.append(f"\nMinor Characters: {len(minor_chars)} characters")

        return "\n".join(lines)

    def get_statistics(self) -> dict[str, Any]:
        """Get character statistics."""
        total = len(self.characters)
        by_gender = {}
        by_importance = {}

        for char in self.characters:
            # Count by gender
            gender_key = char.gender.value
            by_gender[gender_key] = by_gender.get(gender_key, 0) + 1

            # Count by importance
            by_importance[char.importance] = by_importance.get(char.importance, 0) + 1

        return {
            "total": total,
            "by_gender": by_gender,
            "by_importance": by_importance,
            "main_characters": [c.name for c in self.get_main_characters()],
        }

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_statistics()
        return (
            f"CharacterAnalysis(book_id='{self.book_id}', "
            f"total={stats['total']}, by_gender={stats['by_gender']})"
        )
