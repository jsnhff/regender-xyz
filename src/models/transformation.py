"""
Transformation Domain Model

This module defines models for book transformations and their results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from .book import Book, Chapter
from .character import CharacterAnalysis


class TransformType(Enum):
    """Types of gender transformations."""

    ALL_MALE = "all_male"
    ALL_FEMALE = "all_female"
    GENDER_SWAP = "gender_swap"
    NONBINARY = "nonbinary"
    CUSTOM = "custom"

    def get_description(self) -> str:
        """Get human-readable description."""
        descriptions = {
            TransformType.ALL_MALE: "Transform all characters to male",
            TransformType.ALL_FEMALE: "Transform all characters to female",
            TransformType.GENDER_SWAP: "Swap all character genders",
            TransformType.NONBINARY: "Transform to non-binary representation",
            TransformType.CUSTOM: "Custom transformation rules",
        }
        return descriptions.get(self, "Unknown transformation")


@dataclass
class TransformationChange:
    """Represents a single change made during transformation."""

    chapter_index: int
    paragraph_index: int
    sentence_index: int
    original: str
    transformed: str
    change_type: str  # pronoun, name, title, etc.
    character_affected: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "location": {
                "chapter": self.chapter_index,
                "paragraph": self.paragraph_index,
                "sentence": self.sentence_index,
            },
            "original": self.original,
            "transformed": self.transformed,
            "type": self.change_type,
            "character": self.character_affected,
        }


@dataclass
class Transformation:
    """Represents a complete book transformation."""

    original_book: Book
    transformed_chapters: list[Chapter]
    transform_type: TransformType
    characters_used: CharacterAnalysis
    changes: list[TransformationChange] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    quality_score: Optional[float] = None
    qc_iterations: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "original_book_id": self.original_book.hash(),
            "transform_type": self.transform_type.value,
            "chapters": [c.to_dict() for c in self.transformed_chapters],
            "characters": self.characters_used.to_dict(),
            "changes": [c.to_dict() for c in self.changes],
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "quality_score": self.quality_score,
            "qc_iterations": self.qc_iterations,
        }

    def get_transformed_book(self) -> Book:
        """
        Create a Book object from the transformation.

        Returns:
            New Book with transformed content
        """
        return Book(
            title=f"{self.original_book.title} ({self.transform_type.value})",
            author=self.original_book.author,
            chapters=self.transformed_chapters,
            metadata={
                **self.original_book.metadata,
                "transformation": {
                    "type": self.transform_type.value,
                    "timestamp": self.timestamp.isoformat(),
                    "quality_score": self.quality_score,
                    "total_changes": len(self.changes),
                },
            },
        )

    def get_changes_by_type(self) -> dict[str, list[TransformationChange]]:
        """Group changes by type."""
        by_type = {}
        for change in self.changes:
            if change.change_type not in by_type:
                by_type[change.change_type] = []
            by_type[change.change_type].append(change)
        return by_type

    def get_changes_by_character(self) -> dict[str, list[TransformationChange]]:
        """Group changes by character affected."""
        by_character = {}
        for change in self.changes:
            char_name = change.character_affected or "unknown"
            if char_name not in by_character:
                by_character[char_name] = []
            by_character[char_name].append(change)
        return by_character

    def get_statistics(self) -> dict[str, Any]:
        """Get transformation statistics."""
        changes_by_type = self.get_changes_by_type()
        changes_by_character = self.get_changes_by_character()

        return {
            "total_changes": len(self.changes),
            "changes_by_type": {k: len(v) for k, v in changes_by_type.items()},
            "characters_affected": len(changes_by_character),
            "chapters_transformed": len(self.transformed_chapters),
            "quality_score": self.quality_score,
            "qc_iterations": self.qc_iterations,
        }

    def validate(self) -> list[str]:
        """
        Validate the transformation.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check chapter count matches
        original_chapters = len(self.original_book.chapters)
        transformed_chapters = len(self.transformed_chapters)
        if original_chapters != transformed_chapters:
            errors.append(
                f"Chapter count mismatch: original={original_chapters}, "
                f"transformed={transformed_chapters}"
            )

        # Check for empty transformations
        if not self.changes and self.transform_type != TransformType.CUSTOM:
            errors.append("No changes recorded for transformation")

        # Validate quality score if present
        if self.quality_score is not None and not 0 <= self.quality_score <= 100:
            errors.append(f"Invalid quality score: {self.quality_score}")

        return errors

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_statistics()
        return (
            f"Transformation(type={self.transform_type.value}, "
            f"changes={stats['total_changes']}, "
            f"quality={self.quality_score})"
        )


@dataclass
class TransformationResult:
    """Simplified result for backward compatibility."""

    transformed_book: dict[str, Any]
    characters_used: dict[str, Any]
    transform_type: str
    total_changes: int
    processing_time: float
    quality_score: Optional[float] = None
    qc_iterations: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_transformation(
        cls, transformation: Transformation, processing_time: float
    ) -> "TransformationResult":
        """Create from Transformation object."""
        stats = transformation.get_statistics()
        return cls(
            transformed_book=transformation.get_transformed_book().to_dict(),
            characters_used=transformation.characters_used.to_dict(),
            transform_type=transformation.transform_type.value,
            total_changes=stats["total_changes"],
            processing_time=processing_time,
            quality_score=transformation.quality_score,
            qc_iterations=transformation.qc_iterations,
            metadata=transformation.metadata,
        )
