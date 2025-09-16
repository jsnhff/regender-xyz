"""
Transform Service

This service handles gender transformation of books.
"""

import asyncio
import time
from typing import Any, Optional

from src.models.book import Book, Chapter
from src.models.character import CharacterAnalysis
from src.models.transformation import (
    Transformation,
    TransformationChange,
    TransformType,
)
from src.providers.base import LLMProvider
from src.services.base import BaseService, ServiceConfig
from src.strategies.transform import SmartTransformStrategy, TransformStrategy
from src.utils.token_manager import TokenManager

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
        token_manager: Optional[TokenManager] = None,
    ):
        """
        Initialize transform service.

        Args:
            provider: LLM provider for transformations
            character_service: Service for character analysis
            strategy: Transformation strategy
            config: Service configuration
            token_manager: Token manager for consistent estimation
        """
        self.provider = provider
        self.character_service = character_service
        self.strategy = strategy or self._get_default_strategy()
        self.token_manager = token_manager
        super().__init__(config)

    def _initialize(self):
        """Initialize transformation resources."""
        self.transformation_cache = {}

        # Initialize token manager if not provided
        if not self.token_manager:
            if self.provider:
                provider_name = getattr(self.provider, "name", "openai")
                model_name = getattr(self.provider, "model", None)
                self.token_manager = TokenManager.for_provider(provider_name, model_name)
            else:
                self.token_manager = TokenManager()  # Default to GPT-4

        self.logger.info(f"Using TokenManager for {self.token_manager.config.name}")
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
        selected_characters: Optional[list[str]] = None,
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
            context = self._create_context(characters, transform_type, selected_characters)

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
            import traceback

            self.logger.error(f"Transform error: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.handle_error(e, {"book_title": book.title, "transform_type": transform_type.value})

    def _create_context(
        self,
        characters: CharacterAnalysis,
        transform_type: TransformType,
        selected_characters: Optional[list[str]] = None,
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
        characters_to_transform = []
        characters_to_preserve = []

        for char in characters.characters:
            # Check if this character should be transformed
            should_transform = selected_characters is None or char.name in selected_characters

            if should_transform:
                mappings = self._get_character_transformation(char, transform_type)
                character_mappings[char.name] = mappings
                for alias in char.aliases:
                    character_mappings[alias] = mappings
                characters_to_transform.append(char.name)
            else:
                # Preserve original gender
                mappings = {
                    "original_gender": char.gender,
                    "new_gender": char.gender,
                    "pronouns": char.pronouns,
                    "preserve": True,
                }
                character_mappings[char.name] = mappings
                for alias in char.aliases:
                    character_mappings[alias] = mappings
                characters_to_preserve.append(char.name)

        # Create context string for selective transformation
        character_context = self._create_selective_context_string(
            characters, characters_to_transform, characters_to_preserve
        )

        return {
            "transform_type": transform_type,
            "rules": rules,
            "characters": characters,
            "character_mappings": character_mappings,
            "character_context": character_context,
            "characters_to_transform": characters_to_transform,
            "characters_to_preserve": characters_to_preserve,
        }

    def _create_selective_context_string(
        self, characters: CharacterAnalysis, to_transform: list[str], to_preserve: list[str]
    ) -> str:
        """Create context string for selective transformation."""
        lines = []

        if to_transform:
            lines.append("Characters to transform:")
            for name in to_transform:
                char = next((c for c in characters.characters if c.name == name), None)
                if char:
                    lines.append(f"  - {name}: {char.gender.value} -> swap gender")

        if to_preserve:
            lines.append("\nCharacters to preserve (DO NOT change):")
            for name in to_preserve:
                char = next((c for c in characters.characters if c.name == name), None)
                if char:
                    lines.append(f"  - {name}: keep as {char.gender.value}")

        if not lines:
            return characters.create_context_string()

        return "\n".join(lines)

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
        # Check if we should use parallel processing
        use_parallel = len(chapters) > 2 and self.config.async_enabled and self.provider

        if use_parallel:
            return await self._transform_chapters_parallel(chapters, context)
        else:
            return await self._transform_chapters_sequential(chapters, context)

    async def _transform_chapters_sequential(
        self, chapters: list[Chapter], context: dict[str, Any]
    ) -> tuple[list[Chapter], list[TransformationChange]]:
        """Transform chapters sequentially with rate limiting."""
        transformed_chapters = []
        all_changes = []

        # Use rate limiter for OpenAI
        rate_limiter = None
        if self.provider and "openai" in self.provider.name.lower():
            from src.providers.rate_limiter import OpenAIRateLimiter

            rate_limiter = OpenAIRateLimiter(tier="tier-1")
            self.logger.info(f"Using OpenAI rate limiter for {len(chapters)} chapters")

        for i, chapter in enumerate(chapters):
            # Apply rate limiting if needed
            if rate_limiter:
                # Estimate tokens based on chapter content using TokenManager
                chapter_text = " ".join([p.text for p in chapter.paragraphs])
                estimated_tokens = min(self.token_manager.estimate_tokens(chapter_text), 4500)
                await rate_limiter.acquire(estimated_tokens)

                # Track token usage
                self.token_manager.track_usage(
                    input_tokens=estimated_tokens,
                    provider=self.provider.name if self.provider else "unknown",
                )

            self.logger.debug(f"Transforming chapter {i + 1}/{len(chapters)}")

            transformed_chapter, changes = await self._transform_single_chapter(chapter, i, context)

            transformed_chapters.append(transformed_chapter)
            all_changes.extend(changes)

            # Show progress
            if (i + 1) % 5 == 0:
                self.logger.info(f"Progress: {i + 1}/{len(chapters)} chapters transformed")

        return transformed_chapters, all_changes

    async def _transform_chapters_parallel(
        self, chapters: list[Chapter], context: dict[str, Any]
    ) -> tuple[list[Chapter], list[TransformationChange]]:
        """Transform chapters in parallel with rate limiting."""

        # For OpenAI, force sequential processing due to rate limits
        if self.provider and "openai" in self.provider.name.lower():
            self.logger.info("OpenAI detected - using sequential processing for rate limiting")
            return await self._transform_chapters_sequential(chapters, context)

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
        from src.models.book import Chapter, Paragraph
        from src.models.transformation import TransformationChange

        # If no provider, do rule-based transformation
        if not self.provider:
            return await self._rule_based_transform(chapter, chapter_index, context)

        # Use LLM for transformation
        changes = []
        transformed_paragraphs = []

        # Apply rate limiting if needed
        if self.provider and "openai" in self.provider.name.lower():
            from src.providers.rate_limiter import OpenAIRateLimiter

            rate_limiter = OpenAIRateLimiter(tier="tier-1")

            # Estimate tokens for the chapter using TokenManager
            chapter_text = " ".join([p.get_text() for p in chapter.paragraphs])
            estimated_tokens = min(self.token_manager.estimate_tokens(chapter_text), 4500)
            await rate_limiter.acquire(estimated_tokens)

            # Track token usage
            self.token_manager.track_usage(
                input_tokens=estimated_tokens,
                provider=self.provider.name if self.provider else "unknown",
            )

        # Transform each paragraph
        for para_idx, paragraph in enumerate(chapter.paragraphs):
            # Create prompt for transformation
            prompt = self._create_transform_prompt(paragraph.get_text(), context)

            try:
                # Call LLM
                messages = [
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]},
                ]

                response = await self.provider.complete_async(
                    messages=messages,
                    temperature=0.3,  # Low temperature for consistency
                )

                # Debug logging
                original_text = paragraph.get_text()
                if para_idx == 0:  # Log first paragraph for debugging
                    self.logger.debug(f"Original text: {repr(original_text[:100])}")
                    self.logger.debug(f"Transformed text: {repr(response[:100])}")
                    self.logger.debug(f"Are they equal? {response == original_text}")

                # Track changes
                if response != original_text:
                    changes.append(
                        TransformationChange(
                            location=f"Chapter {chapter_index + 1}, Paragraph {para_idx + 1}",
                            original=paragraph.get_text(),
                            transformed=response,
                            change_type="gender_swap",
                        )
                    )

                # Create transformed paragraph
                transformed_paragraphs.append(Paragraph(sentences=[response]))

            except Exception as e:
                self.logger.warning(f"Failed to transform paragraph {para_idx}: {e}")
                # Keep original on error
                transformed_paragraphs.append(paragraph)

        # Create transformed chapter
        transformed_chapter = Chapter(
            number=chapter.number, title=chapter.title, paragraphs=transformed_paragraphs
        )

        return transformed_chapter, changes

    async def _rule_based_transform(
        self, chapter: Chapter, chapter_index: int, context: dict[str, Any]
    ) -> tuple[Chapter, list[TransformationChange]]:
        """Apply rule-based transformation without LLM."""
        import re

        from src.models.book import Chapter, Paragraph
        from src.models.transformation import TransformationChange

        changes = []
        transformed_paragraphs = []

        # Get transformation rules
        rules = context.get("rules", {})
        pronouns = rules.get("pronouns", {})
        titles = rules.get("titles", {})
        terms = rules.get("terms", {})

        for para_idx, paragraph in enumerate(chapter.paragraphs):
            text = paragraph.get_text()
            original_text = text

            # Apply pronoun swaps (case-sensitive with word boundaries)
            for old, new in pronouns.items():
                # Handle capitalized versions
                text = re.sub(r"\b" + old.capitalize() + r"\b", new.capitalize(), text)
                text = re.sub(r"\b" + old + r"\b", new, text)

            # Apply title swaps
            for old, new in titles.items():
                text = text.replace(old, new)

            # Apply term swaps (case-insensitive)
            for old, new in terms.items():
                text = re.sub(r"\b" + old + r"\b", new, text, flags=re.IGNORECASE)
                text = re.sub(r"\b" + old.capitalize() + r"\b", new.capitalize(), text)

            # Track changes
            if text != original_text:
                changes.append(
                    TransformationChange(
                        location=f"Chapter {chapter_index + 1}, Paragraph {para_idx + 1}",
                        original=original_text,
                        transformed=text,
                        change_type="rule_based_swap",
                    )
                )

            # Create transformed paragraph
            # Split text into sentences
            sentences = [s.strip() + "." for s in text.split(". ") if s.strip()]
            if text and not sentences:  # Handle text without periods
                sentences = [text]
            transformed_paragraphs.append(Paragraph(sentences=sentences))

        # Create transformed chapter
        transformed_chapter = Chapter(
            number=chapter.number, title=chapter.title, paragraphs=transformed_paragraphs
        )

        return transformed_chapter, changes

    def _create_transform_prompt(self, text: str, context: dict[str, Any]) -> dict[str, str]:
        """Create prompt for LLM transformation."""
        character_context = context.get("character_context", "")
        transform_type = context.get("transform_type", "gender_swap")
        to_preserve = context.get("characters_to_preserve", [])

        preserve_instruction = ""
        if to_preserve:
            preserve_instruction = f"\nIMPORTANT: DO NOT change the gender of these characters: {', '.join(to_preserve)}"

        system_prompt = f"""You are a literary text transformer specializing in gender representation changes.
Your task is to transform the given text according to the '{transform_type}' transformation type.

Character context:
{character_context}
{preserve_instruction}

Transformation rules:
- Only transform characters listed in "Characters to transform" above
- Keep all other characters' genders unchanged
- Swap gendered pronouns ONLY for characters being transformed
- Update gendered terms (mother/father, sister/brother, etc.) ONLY for transformed characters
- Maintain the original style, tone, and meaning
- Preserve proper names but update titles (Mr./Mrs./Ms.) where appropriate
- Keep the narrative flow natural

Return ONLY the transformed text, no explanations."""

        user_prompt = f"""Transform this text using '{transform_type}' rules:

{text}"""

        return {"system": system_prompt, "user": user_prompt}

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

        # Add token usage metrics
        if self.token_manager:
            metrics["token_usage"] = self.token_manager.get_usage_stats()
            metrics["model_info"] = self.token_manager.get_model_info()

        return metrics
