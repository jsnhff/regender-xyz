"""
Character Service

This service handles character analysis and gender identification in books.
"""

from typing import Dict, List, Optional, Any
import json
import hashlib
from datetime import datetime

from src.services.base import BaseService, ServiceConfig
from src.models.book import Book
from src.models.character import Character, CharacterAnalysis, Gender
from src.strategies.analysis import AnalysisStrategy, SmartChunkingStrategy
from src.providers.base import LLMProvider


class CharacterCache:
    """Simple character analysis cache."""
    
    def __init__(self):
        self.cache = {}
    
    async def get_async(self, key: str) -> Optional[CharacterAnalysis]:
        """Get cached analysis."""
        return self.cache.get(key)
    
    async def set_async(self, key: str, value: CharacterAnalysis) -> None:
        """Cache analysis."""
        self.cache[key] = value


class CharacterMerger:
    """Merges character results from multiple chunks."""
    
    def merge(self, chunk_results: List[Dict[str, Any]]) -> List[Character]:
        """
        Merge character results from multiple chunks.
        
        Args:
            chunk_results: List of analysis results from chunks
            
        Returns:
            Merged list of characters
        """
        character_map = {}
        
        for result in chunk_results:
            for char_data in result.get('characters', []):
                name = char_data.get('name')
                if not name:
                    continue
                
                if name not in character_map:
                    # Ensure aliases and titles are lists
                    aliases = char_data.get('aliases', [])
                    if aliases is None:
                        aliases = []
                    elif isinstance(aliases, str):
                        aliases = [aliases] if aliases else []
                    
                    titles = char_data.get('titles', [])
                    if titles is None:
                        titles = []
                    elif isinstance(titles, str):
                        titles = [titles] if titles else []
                    
                    # Create new character
                    character_map[name] = Character(
                        name=name,
                        gender=Gender(char_data.get('gender', 'unknown')),
                        pronouns=char_data.get('pronouns', {}),
                        titles=titles,
                        aliases=aliases,
                        description=char_data.get('description'),
                        importance=char_data.get('importance', 'supporting'),
                        confidence=char_data.get('confidence', 1.0)
                    )
                else:
                    # Merge with existing
                    existing = character_map[name]
                    
                    # Update importance if more significant
                    importance_rank = {'minor': 0, 'supporting': 1, 'main': 2}
                    if importance_rank.get(char_data.get('importance', 'minor'), 0) > \
                       importance_rank.get(existing.importance, 0):
                        existing.importance = char_data.get('importance')
                    
                    # Merge aliases - handle both string and list
                    aliases = char_data.get('aliases', [])
                    if aliases is None:
                        aliases = []
                    elif isinstance(aliases, str):
                        aliases = [aliases] if aliases else []
                    for alias in aliases:
                        if alias and alias not in existing.aliases:
                            existing.aliases.append(alias)
                    
                    # Average confidence
                    existing.confidence = (existing.confidence + char_data.get('confidence', 1.0)) / 2
        
        return list(character_map.values())


class PromptGenerator:
    """Generates prompts for character analysis."""
    
    def generate_analysis_prompt(self, text: str) -> Dict[str, str]:
        """
        Generate character analysis prompt.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with system and user prompts
        """
        system_prompt = """You are a literary character analyzer. Your task is to identify all characters mentioned in the text and determine their gender based on context clues like pronouns, titles, and descriptions.

For each character, provide:
1. Name (full name if available)
2. Gender (male, female, non-binary, or unknown)
3. Pronouns used (subject/object/possessive)
4. Any titles (Mr., Mrs., Dr., etc.)
5. Aliases or nicknames
6. Brief description if available
7. Importance (main, supporting, or minor)
8. Confidence level (0-1)

Output as JSON with a 'characters' array."""
        
        user_prompt = f"""Analyze the following text and identify all characters with their genders:

{text}

Remember to output valid JSON with a 'characters' array containing the character information."""
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }


class CharacterService(BaseService):
    """
    Service for character analysis.
    
    This service:
    - Analyzes books to identify characters
    - Determines character genders
    - Provides character context for transformations
    """
    
    def __init__(self,
                 provider: Optional[LLMProvider] = None,
                 strategy: Optional[AnalysisStrategy] = None,
                 config: Optional[ServiceConfig] = None):
        """
        Initialize character service.
        
        Args:
            provider: LLM provider for analysis
            strategy: Analysis strategy
            config: Service configuration
        """
        self.provider = provider
        self.strategy = strategy or self._get_default_strategy()
        super().__init__(config)
    
    def _initialize(self):
        """Initialize character analysis resources."""
        self.prompt_generator = PromptGenerator()
        self.character_merger = CharacterMerger()
        self.cache = CharacterCache() if self.config.cache_enabled else None
        
        self.logger.info(f"Initialized {self.__class__.__name__}")
    
    def _get_default_strategy(self) -> AnalysisStrategy:
        """Get default analysis strategy."""
        return SmartChunkingStrategy()
    
    async def process_async(self, book: Book) -> CharacterAnalysis:
        """
        Analyze characters in a book.
        
        Args:
            book: Book to analyze
            
        Returns:
            Character analysis results
        """
        # Check cache
        book_hash = book.hash()
        if self.cache:
            cached = await self.cache.get_async(book_hash)
            if cached:
                self.logger.info(f"Using cached character analysis for {book_hash}")
                return cached
        
        try:
            # Extract text for analysis
            text_chunks = await self.strategy.chunk_book_async(book)
            self.logger.info(f"Created {len(text_chunks)} chunks for analysis")
            
            # Analyze each chunk
            chunk_results = await self._analyze_chunks_async(text_chunks)
            
            # Merge results
            characters = self.character_merger.merge(chunk_results)
            self.logger.info(f"Identified {len(characters)} characters")
            
            # Create analysis result
            analysis = CharacterAnalysis(
                book_id=book_hash,
                characters=characters,
                metadata=self._generate_metadata(characters),
                provider=self.provider.name if self.provider else "unknown",
                model=getattr(self.provider, 'model', 'unknown') if self.provider else "unknown"
            )
            
            # Cache result
            if self.cache:
                await self.cache.set_async(book_hash, analysis)
            
            return analysis
            
        except Exception as e:
            self.handle_error(e, {"book_title": book.title})
    
    async def _analyze_chunks_async(self, chunks: List[str]) -> List[Dict]:
        """
        Analyze text chunks in parallel.
        
        Args:
            chunks: Text chunks to analyze
            
        Returns:
            List of analysis results
        """
        import asyncio
        
        # If no provider, return mock results
        if not self.provider:
            self.logger.warning("No LLM provider configured, returning mock results")
            return [{"characters": []} for _ in chunks]
        
        # Create analysis tasks
        tasks = [
            self._analyze_single_chunk(chunk, idx)
            for idx, chunk in enumerate(chunks)
        ]
        
        # Limit concurrency based on provider
        if self.provider:
            if 'grok' in self.provider.name.lower():
                max_concurrent = 1  # Grok has strict rate limits
            elif 'openai' in self.provider.name.lower():
                max_concurrent = 10  # OpenAI handles parallel requests well
            else:
                max_concurrent = self.config.max_concurrent
        else:
            max_concurrent = self.config.max_concurrent
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(*[limited_task(t) for t in tasks])
        return results
    
    async def _analyze_single_chunk(self, chunk: str, chunk_index: int) -> Dict[str, Any]:
        """
        Analyze a single text chunk.
        
        Args:
            chunk: Text to analyze
            chunk_index: Index of the chunk
            
        Returns:
            Analysis results
        """
        self.logger.debug(f"Analyzing chunk {chunk_index}")
        
        # Generate prompt
        prompts = self.prompt_generator.generate_analysis_prompt(chunk)
        
        # Create messages
        messages = [
            {"role": "system", "content": prompts["system"]},
            {"role": "user", "content": prompts["user"]}
        ]
        
        try:
            # Call LLM
            response = await self.provider.complete_async(
                messages=messages,
                temperature=0.1,  # Low temperature for consistency
                response_format={"type": "json_object"} if self.provider.supports_json else None
            )
            
            # Parse response
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                self.logger.warning(f"Failed to parse JSON from chunk {chunk_index}")
                result = {"characters": []}
            
            result["chunk_index"] = chunk_index
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing chunk {chunk_index}: {e}")
            return {"chunk_index": chunk_index, "characters": []}
    
    def _generate_metadata(self, characters: List[Character]) -> Dict[str, Any]:
        """
        Generate metadata about the analysis.
        
        Args:
            characters: List of identified characters
            
        Returns:
            Metadata dictionary
        """
        stats = {
            "total": len(characters),
            "by_gender": {},
            "by_importance": {}
        }
        
        for char in characters:
            # Count by gender
            gender_key = char.gender.value
            stats["by_gender"][gender_key] = stats["by_gender"].get(gender_key, 0) + 1
            
            # Count by importance
            stats["by_importance"][char.importance] = \
                stats["by_importance"].get(char.importance, 0) + 1
        
        return stats
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        metrics = super().get_metrics()
        metrics.update({
            "provider": self.provider.name if self.provider else "none",
            "strategy": self.strategy.__class__.__name__,
            "cache_size": len(self.cache.cache) if self.cache else 0
        })
        return metrics