"""
Book Domain Model

This module defines the core book structure used throughout
the application.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Paragraph:
    """Represents a paragraph in a book."""

    sentences: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {"sentences": self.sentences}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Paragraph":
        """Create from dictionary representation."""
        return cls(sentences=data.get("sentences", []))

    def get_text(self) -> str:
        """Get full text of the paragraph."""
        return " ".join(self.sentences)

    def word_count(self) -> int:
        """Get word count of the paragraph."""
        return sum(len(sentence.split()) for sentence in self.sentences)


@dataclass
class Chapter:
    """Represents a chapter in a book."""

    number: Optional[int]
    title: Optional[str]
    paragraphs: List[Paragraph]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "number": self.number,
            "title": self.title,
            "paragraphs": [p.to_dict() for p in self.paragraphs],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chapter":
        """Create from dictionary representation."""
        return cls(
            number=data.get("number"),
            title=data.get("title"),
            paragraphs=[Paragraph.from_dict(p) for p in data.get("paragraphs", [])],
            metadata=data.get("metadata", {}),
        )

    def get_text(self) -> str:
        """Get full text of the chapter."""
        return "\n\n".join(p.get_text() for p in self.paragraphs)

    def get_sentences(self) -> List[str]:
        """Get all sentences in the chapter."""
        sentences = []
        for paragraph in self.paragraphs:
            sentences.extend(paragraph.sentences)
        return sentences

    def word_count(self) -> int:
        """Get word count of the chapter."""
        return sum(p.word_count() for p in self.paragraphs)


@dataclass
class Book:
    """Represents a complete book."""

    title: Optional[str]
    author: Optional[str]
    chapters: List[Chapter]
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "metadata": {"title": self.title, "author": self.author, **self.metadata},
            "chapters": [c.to_dict() for c in self.chapters],
            "source_file": self.source_file,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Book":
        """Create from dictionary representation."""
        metadata = data.get("metadata", {})
        return cls(
            title=metadata.get("title"),
            author=metadata.get("author"),
            chapters=[Chapter.from_dict(c) for c in data.get("chapters", [])],
            metadata={k: v for k, v in metadata.items() if k not in ["title", "author"]},
            source_file=data.get("source_file"),
        )

    def get_text(self) -> str:
        """Get full text of the book."""
        chapter_texts = []
        for chapter in self.chapters:
            if chapter.title:
                chapter_texts.append(f"# {chapter.title}\n")
            chapter_texts.append(chapter.get_text())
        return "\n\n".join(chapter_texts)

    def get_chapter(self, number: int) -> Optional[Chapter]:
        """Get a chapter by number."""
        for chapter in self.chapters:
            if chapter.number == number:
                return chapter
        return None

    def word_count(self) -> int:
        """Get total word count of the book."""
        return sum(c.word_count() for c in self.chapters)

    def chapter_count(self) -> int:
        """Get number of chapters."""
        return len(self.chapters)

    def hash(self) -> str:
        """
        Generate a unique hash for the book.

        This is used for caching and deduplication.
        """
        # Create a stable representation
        book_repr = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(book_repr.encode()).hexdigest()[:16]

    def validate(self) -> List[str]:
        """
        Validate the book structure.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.chapters:
            errors.append("Book has no chapters")

        for i, chapter in enumerate(self.chapters):
            if not chapter.paragraphs:
                errors.append(f"Chapter {i + 1} has no paragraphs")

            for j, paragraph in enumerate(chapter.paragraphs):
                if not paragraph.sentences:
                    errors.append(f"Chapter {i + 1}, Paragraph {j + 1} has no sentences")

        return errors

    def __repr__(self) -> str:
        """String representation of the book."""
        return (
            f"Book(title='{self.title}', author='{self.author}', "
            f"chapters={len(self.chapters)}, words={self.word_count()})"
        )
