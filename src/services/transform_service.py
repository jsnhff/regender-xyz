"""
Transform Service

This service handles gender transformation of books.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.models.book import Book, Chapter, Paragraph
from src.models.character import CharacterAnalysis
from src.models.transformation import (
    Transformation,
    TransformationChange,
    TransformationResult,
    TransformType,
)
from src.providers.base import LLMProvider
from src.services.base import BaseService, ServiceConfig
from src.strategies.transform import SmartTransformStrategy, TransformStrategy

from .character_service import CharacterService


class TransformService(BaseService):
    """
    Service for gender transformation.

    This service:
    - Transforms books based on gender rules
    - Maintains consistency across the text
    - Tracks all changes made
    - Supports various transformation types
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        character_service: Optional[CharacterService] = None,
        strategy: Optional[TransformStrategy] = None,
        config: Optional[ServiceConfig] = None,
    ):
        """
        Initialize transform service.

        Args:
            provider: LLM provider for transformations
            character_service: Service for character analysis
            strategy: Transformation strategy
            config: Service configuration
        """
        self.provider = provider
        self.character_service = character_service
        self.strategy = strategy or self._get_default_strategy()
        super().__init__(config)

    def _initialize(self):
        """Initialize transformation resources."""
        self.transformation_cache = {}
        self.logger.info(f"Initialized {self.__class__.__name__}")

    def _get_default_strategy(self) -> TransformStrategy:
        """Get default transformation strategy."""
        return SmartTransformStrategy()

    async def process_async(self, data: dict[str, Any]) -> Transformation:
        """
        Transform a book's gender representation.

        Args:
            data: Dictionary containing:
                - book: Book object
                - transform_type: TransformType or string
                - characters: Optional CharacterAnalysis

        Returns:
            Transformation result
        """
        # Extract parameters
        book = data.get("book")
        if not isinstance(book, Book):
            raise ValueError("'book' must be a Book object")

        transform_type = data.get("transform_type")
        if isinstance(transform_type, str):
            transform_type = TransformType(transform_type)
        elif not isinstance(transform_type, TransformType):
            raise ValueError("'transform_type' must be a TransformType or string")

        characters = data.get("characters")

        return await self.transform_book_async(book, transform_type, characters)

    async def transform_book_async(
        self,
        book: Book,
        transform_type: TransformType,
        characters: Optional[CharacterAnalysis] = None,
    ) -> Transformation:
        """
        Transform a book with the specified transformation type.

        Args:
            book: Book to transform
            transform_type: Type of transformation
            characters: Pre-analyzed characters (optional)

        Returns:
            Transformation object with results
        """
        start_time = time.time()

        try:
            # Get character analysis if not provided
            if not characters:
                if not self.character_service:
                    raise ValueError("Character service required when characters not provided")

                self.logger.info("Analyzing characters...")
                characters = await self.character_service.process_async(book)

            # Create transformation context
            context = self._create_context(characters, transform_type)

            # Transform chapters
            self.logger.info(f"Transforming {len(book.chapters)} chapters...")
            transformed_chapters, all_changes = await self._transform_chapters_async(
                book.chapters, context
            )

            # Create transformation result
            transformation = Transformation(
                original_book=book,
                transformed_chapters=transformed_chapters,
                transform_type=transform_type,
                characters_used=characters,
                changes=all_changes,
                metadata={
                    "provider": self.provider.name if self.provider else "mock",
                    "strategy": self.strategy.__class__.__name__,
                    "processing_time": time.time() - start_time,
                },
            )

            self.logger.info(
                f"Transformation complete: {len(all_changes)} changes in "
                f"{time.time() - start_time:.1f}s"
            )

            return transformation

        except Exception as e:
            self.handle_error(e, {"book_title": book.title, "transform_type": transform_type.value})

    def _create_context(
        self, characters: CharacterAnalysis, transform_type: TransformType
    ) -> dict[str, Any]:
        """
        Create transformation context.

        Args:
            characters: Character analysis
            transform_type: Transformation type

        Returns:
            Context dictionary for transformation
        """
        # Get transformation rules based on type
        rules = self._get_transformation_rules(transform_type)

        # Create character mappings
        character_mappings = {}
        for char in characters.characters:
            mappings = self._get_character_transformation(char, transform_type)
            character_mappings[char.name] = mappings
            for alias in char.aliases:
                character_mappings[alias] = mappings

        return {
            "transform_type": transform_type,
            "rules": rules,
            "characters": characters,
            "character_mappings": character_mappings,
            "character_context": characters.create_context_string(),
        }

    def _get_transformation_rules(self, transform_type: TransformType) -> dict[str, Any]:
        """Get transformation rules for the specified type."""
        if transform_type == TransformType.ALL_MALE:
            return {
                "target_gender": "male",
                "pronouns": {"she": "he", "her": "him", "hers": "his"},
                "titles": {"Mrs.": "Mr.", "Ms.": "Mr.", "Miss": "Mr."},
                "terms": {
                    "mother": "father",
                    "daughter": "son",
                    "sister": "brother",
                    "wife": "husband",
                    "queen": "king",
                    "lady": "lord",
                },
            }
        elif transform_type == TransformType.ALL_FEMALE:
            return {
                "target_gender": "female",
                "pronouns": {"he": "she", "him": "her", "his": "hers"},
                "titles": {"Mr.": "Ms."},
                "terms": {
                    "father": "mother",
                    "son": "daughter",
                    "brother": "sister",
                    "husband": "wife",
                    "king": "queen",
                    "lord": "lady",
                },
            }
        elif transform_type == TransformType.GENDER_SWAP:
            return {
                "swap": True,
                "pronouns": {
                    "he": "she",
                    "she": "he",
                    "him": "her",
                    "her": "him",
                    "his": "hers",
                    "hers": "his",
                },
                "titles": {"Mr.": "Ms.", "Mrs.": "Mr.", "Ms.": "Mr.", "Miss": "Mr."},
                "terms": {
                    "father": "mother",
                    "mother": "father",
                    "son": "daughter",
                    "daughter": "son",
                    "brother": "sister",
                    "sister": "brother",
                    "husband": "wife",
                    "wife": "husband",
                    "king": "queen",
                    "queen": "king",
                    "lord": "lady",
                    "lady": "lord",
                },
            }
        else:
            return {}

    def _get_character_transformation(self, character, transform_type: TransformType) -> dict:
        """Get transformation mappings for a specific character."""
        from src.models.character import Gender

        mappings = {"original_gender": character.gender}

        if transform_type == TransformType.ALL_MALE:
            mappings["new_gender"] = Gender.MALE
            mappings["pronouns"] = {"subject": "he", "object": "him", "possessive": "his"}
        elif transform_type == TransformType.ALL_FEMALE:
            mappings["new_gender"] = Gender.FEMALE
            mappings["pronouns"] = {"subject": "she", "object": "her", "possessive": "her"}
        elif transform_type == TransformType.GENDER_SWAP:
            if character.gender == Gender.MALE:
                mappings["new_gender"] = Gender.FEMALE
                mappings["pronouns"] = {"subject": "she", "object": "her", "possessive": "her"}
            elif character.gender == Gender.FEMALE:
                mappings["new_gender"] = Gender.MALE
                mappings["pronouns"] = {"subject": "he", "object": "him", "possessive": "his"}
            else:
                mappings["new_gender"] = character.gender
                mappings["pronouns"] = character.pronouns

        return mappings

    async def _transform_chapters_async(
        self, chapters: list[Chapter], context: dict[str, Any]
    ) -> tuple[list[Chapter], list[TransformationChange]]:
        """
        Transform chapters with the given context.

        Args:
            chapters: Chapters to transform
            context: Transformation context

        Returns:
            Tuple of (transformed chapters, list of changes)
        """
        if not self.provider:
            # Mock transformation without provider
            self.logger.warning("No provider configured, returning original chapters")
            return chapters, []

        # Check if we should use parallel processing
        use_parallel = len(chapters) > 2 and self.config.async_enabled

        if use_parallel:
            return await self._transform_chapters_parallel(chapters, context)
        else:
            return await self._transform_chapters_sequential(chapters, context)

    async def _transform_chapters_sequential(
        self, chapters: list[Chapter], context: dict[str, Any]
    ) -> tuple[list[Chapter], list[TransformationChange]]:
        """Transform chapters sequentially."""
        transformed_chapters = []
        all_changes = []

        for i, chapter in enumerate(chapters):
            self.logger.debug(f"Transforming chapter {i + 1}/{len(chapters)}")

            transformed_chapter, changes = await self._transform_single_chapter(chapter, i, context)

            transformed_chapters.append(transformed_chapter)
            all_changes.extend(changes)

        return transformed_chapters, all_changes

    async def _transform_chapters_parallel(
        self, chapters: list[Chapter], context: dict[str, Any]
    ) -> tuple[list[Chapter], list[TransformationChange]]:
        """Transform chapters in parallel."""

        # Create tasks for each chapter
        tasks = [
            self._transform_single_chapter(chapter, i, context)
            for i, chapter in enumerate(chapters)
        ]

        # Limit concurrency
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def limited_task(task):
            async with semaphore:
                return await task

        # Execute all tasks
        results = await asyncio.gather(*[limited_task(t) for t in tasks])

        # Separate chapters and changes
        transformed_chapters = []
        all_changes = []

        for transformed_chapter, changes in results:
            transformed_chapters.append(transformed_chapter)
            all_changes.extend(changes)

        return transformed_chapters, all_changes

    async def _transform_single_chapter(
        self, chapter: Chapter, chapter_index: int, context: dict[str, Any]
    ) -> tuple[Chapter, list[TransformationChange]]:
        """
        Transform a single chapter.

        Args:
            chapter: Chapter to transform
            chapter_index: Index of the chapter
            context: Transformation context

        Returns:
            Tuple of (transformed chapter, list of changes)
        """
        # For now, use existing transformation logic
        # In production, this would call the LLM provider

        # Mock transformation - just return original
        # Real implementation would use book_transformer.py logic
        return chapter, []

    def get_metrics(self) -> dict[str, Any]:
        """Get service metrics."""
        metrics = super().get_metrics()
        metrics.update(
            {
                "provider": self.provider.name if self.provider else "none",
                "strategy": self.strategy.__class__.__name__,
                "cache_size": len(self.transformation_cache),
            }
        )
        return metrics
