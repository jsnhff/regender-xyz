"""
Unified Character Analyzer with Pluggable Strategies

This module consolidates all character analysis functionality into a single,
extensible interface with different chunking strategies.
"""

import json
import hashlib
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from api_client import UnifiedLLMClient
from book_transform.utils import safe_api_call
from .prompts import get_character_analysis_prompt
from .context import create_character_context


class ChunkingStrategy(Enum):
    """Available chunking strategies for character analysis."""
    SEQUENTIAL = "sequential"
    SMART = "smart"
    RATE_LIMITED = "rate_limited"


class ChunkingStrategyBase(ABC):
    """Abstract base class for chunking strategies."""
    
    @abstractmethod
    def chunk_text(self, text: str, max_tokens: int) -> List[str]:
        """
        Chunk text according to the strategy.
        
        Args:
            text: Full text to chunk
            max_tokens: Maximum tokens per chunk
            
        Returns:
            List of text chunks
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a description of this strategy."""
        pass


class SequentialChunking(ChunkingStrategyBase):
    """Simple sequential chunking - splits text into equal-sized chunks."""
    
    def chunk_text(self, text: str, max_tokens: int) -> List[str]:
        """Split text into sequential chunks."""
        # Estimate 4 characters per token
        chars_per_chunk = max_tokens * 4
        chunks = []
        
        for i in range(0, len(text), chars_per_chunk):
            chunk = text[i:i + chars_per_chunk]
            chunks.append(chunk)
        
        return chunks
    
    def get_description(self) -> str:
        return "Sequential chunking - simple equal-sized chunks"


class SmartChunking(ChunkingStrategyBase):
    """Smart chunking that preserves chapter boundaries and context."""
    
    def chunk_text(self, text: str, max_tokens: int) -> List[str]:
        """Smart chunking with chapter awareness."""
        from book_transform.chunking.token_utils import estimate_tokens
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        # Split by chapters or major sections
        sections = text.split('\nCHAPTER')
        
        for section in sections:
            if section.strip():
                section_text = 'CHAPTER' + section if section != sections[0] else section
                section_tokens = estimate_tokens(section_text)
                
                if current_tokens + section_tokens > max_tokens and current_chunk:
                    # Save current chunk and start new one
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = [section_text]
                    current_tokens = section_tokens
                else:
                    current_chunk.append(section_text)
                    current_tokens += section_tokens
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def get_description(self) -> str:
        return "Smart chunking - preserves chapter boundaries"


class RateLimitedChunking(ChunkingStrategyBase):
    """Chunking optimized for rate-limited APIs."""
    
    def __init__(self, tokens_per_minute: int = 16000):
        self.tokens_per_minute = tokens_per_minute
        self.tokens_per_chunk = min(4000, tokens_per_minute // 4)  # Conservative chunk size
    
    def chunk_text(self, text: str, max_tokens: int) -> List[str]:
        """Chunk text for rate-limited processing."""
        # Use smaller chunks to stay within rate limits
        effective_max = min(max_tokens, self.tokens_per_chunk)
        
        # Use smart chunking but with smaller size
        smart_chunker = SmartChunking()
        return smart_chunker.chunk_text(text, effective_max)
    
    def get_description(self) -> str:
        return f"Rate-limited chunking - optimized for {self.tokens_per_minute} tokens/min"


class UnifiedCharacterAnalyzer:
    """
    Unified character analyzer with pluggable strategies.
    
    This class consolidates all character analysis functionality,
    replacing the multiple analyzer implementations.
    """
    
    def __init__(self, 
                 strategy: ChunkingStrategy = ChunkingStrategy.SMART,
                 provider: Optional[str] = None,
                 model: Optional[str] = None,
                 cache_enabled: bool = True,
                 verbose: bool = True):
        """
        Initialize the unified analyzer.
        
        Args:
            strategy: Chunking strategy to use
            provider: LLM provider
            model: Model name
            cache_enabled: Whether to use caching
            verbose: Whether to print progress
        """
        self.strategy = self._get_strategy(strategy)
        self.provider = provider
        self.model = model
        self.cache_enabled = cache_enabled
        self.verbose = verbose
        self.client = UnifiedLLMClient(provider=provider)
    
    def _get_strategy(self, strategy: ChunkingStrategy) -> ChunkingStrategyBase:
        """Get the appropriate strategy implementation."""
        strategies = {
            ChunkingStrategy.SEQUENTIAL: SequentialChunking(),
            ChunkingStrategy.SMART: SmartChunking(),
            ChunkingStrategy.RATE_LIMITED: RateLimitedChunking()
        }
        return strategies[strategy]
    
    def _get_cache_key(self, book_data: Dict[str, Any]) -> str:
        """Generate a cache key from book data."""
        book_str = json.dumps(book_data, sort_keys=True)
        return hashlib.md5(book_str.encode()).hexdigest()
    
    def _load_cache(self, cache_key: str) -> Optional[Tuple[Dict[str, Any], str]]:
        """Load cached analysis if available."""
        if not self.cache_enabled:
            return None
        
        cache_dir = Path(".cache/characters")
        cache_file = cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    if self.verbose:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Using cached character analysis")
                    return data.get('characters', {}), data.get('context', '')
            except Exception as e:
                if self.verbose:
                    print(f"Cache load error: {e}")
        return None
    
    def _save_cache(self, cache_key: str, characters: Dict[str, Any], context: str):
        """Save analysis to cache."""
        if not self.cache_enabled:
            return
        
        cache_dir = Path(".cache/characters")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        cache_file = cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'characters': characters,
                    'context': context,
                    'timestamp': datetime.now().isoformat(),
                    'strategy': self.strategy.get_description()
                }, f, indent=2)
        except Exception as e:
            if self.verbose:
                print(f"Cache save error: {e}")
    
    def _extract_text(self, book_data: Dict[str, Any]) -> str:
        """Extract full text from book data."""
        full_text = []
        
        for chapter in book_data.get('chapters', []):
            if chapter.get('title'):
                full_text.append(f"\nCHAPTER: {chapter['title']}\n")
            
            for paragraph in chapter.get('paragraphs', []):
                para_text = ' '.join(paragraph.get('sentences', []))
                if para_text:
                    full_text.append(para_text)
        
        return '\n'.join(full_text)
    
    def _analyze_chunk(self, chunk: str) -> Dict[str, Any]:
        """Analyze a single text chunk."""
        system_prompt, user_prompt = get_character_analysis_prompt(
            text=chunk,
            model=self.model,
            provider=self.provider
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.client.complete(
            messages=messages,
            model=self.model,
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        try:
            content = response.content.strip()
            analysis = json.loads(content)
            return analysis.get('characters', {})
        except json.JSONDecodeError as e:
            if self.verbose:
                print(f"JSON decode error: {e}")
            return {}
    
    def _merge_characters(self, 
                         existing: Dict[str, Any], 
                         new: Dict[str, Any]) -> Dict[str, Any]:
        """Merge character data from multiple chunks."""
        merged = existing.copy()
        
        for char_name, char_data in new.items():
            if char_name in merged:
                # Merge name variants
                existing_variants = set(merged[char_name].get('name_variants', []))
                new_variants = set(char_data.get('name_variants', []))
                merged[char_name]['name_variants'] = list(existing_variants | new_variants)
                
                # Merge relationships
                existing_rels = merged[char_name].get('relationships', {})
                new_rels = char_data.get('relationships', {})
                merged[char_name]['relationships'] = {**existing_rels, **new_rels}
                
                # Keep most detailed role description
                if len(char_data.get('role', '')) > len(merged[char_name].get('role', '')):
                    merged[char_name]['role'] = char_data['role']
            else:
                merged[char_name] = char_data
        
        return merged
    
    def analyze(self, 
                book_data: Dict[str, Any],
                max_tokens_per_chunk: Optional[int] = None) -> Tuple[Dict[str, Any], str]:
        """
        Analyze characters in a book.
        
        Args:
            book_data: Book data dictionary
            max_tokens_per_chunk: Maximum tokens per chunk (auto-detected if None)
            
        Returns:
            Tuple of (characters_dict, character_context_string)
        """
        # Check cache
        cache_key = self._get_cache_key(book_data)
        cached = self._load_cache(cache_key)
        if cached:
            return cached
        
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting character analysis")
            print(f"  Strategy: {self.strategy.get_description()}")
        
        # Extract text
        full_text = self._extract_text(book_data)
        
        if self.verbose:
            print(f"  Book length: {len(full_text)} characters")
        
        # Determine max tokens if not specified
        if max_tokens_per_chunk is None:
            from book_transform.model_config_loader import get_verified_model_config
            config = get_verified_model_config(self.model, self.provider)
            if config:
                max_tokens_per_chunk = int(config.context_window * 0.7)
            else:
                max_tokens_per_chunk = 8000  # Conservative default
        
        # Chunk text
        chunks = self.strategy.chunk_text(full_text, max_tokens_per_chunk)
        
        if self.verbose:
            print(f"  Processing {len(chunks)} chunks...")
        
        # Analyze chunks
        all_characters = {}
        for i, chunk in enumerate(chunks):
            if self.verbose:
                print(f"  Chunk {i+1}/{len(chunks)}", end='', flush=True)
            
            try:
                chunk_characters = self._analyze_chunk(chunk)
                all_characters = self._merge_characters(all_characters, chunk_characters)
                
                if self.verbose:
                    print(f" ✓ ({len(chunk_characters)} characters)")
            except Exception as e:
                if self.verbose:
                    print(f" ❌ Error: {e}")
                raise
        
        # Create character context
        character_context = create_character_context(all_characters)
        
        if self.verbose:
            print(f"  Total characters found: {len(all_characters)}")
        
        # Save to cache
        self._save_cache(cache_key, all_characters, character_context)
        
        return all_characters, character_context


# Compatibility functions for backward compatibility
def analyze_book_characters(book_data: Dict[str, Any], 
                           model: Optional[str] = None,
                           provider: Optional[str] = None,
                           sample_size: int = 50000,
                           verbose: bool = True) -> Tuple[Dict[str, Any], str]:
    """
    Backward compatibility wrapper for the unified analyzer.
    
    This function maintains the same interface as the old analyzer.py
    """
    analyzer = UnifiedCharacterAnalyzer(
        strategy=ChunkingStrategy.SMART,
        provider=provider,
        model=model,
        verbose=verbose
    )
    return analyzer.analyze(book_data)


def analyze_book_with_rate_limits(book_data: Dict[str, Any],
                                 model: Optional[str] = None,
                                 provider: Optional[str] = None,
                                 tokens_per_minute: int = 16000,
                                 verbose: bool = True) -> Tuple[Dict[str, Any], str]:
    """
    Backward compatibility wrapper for rate-limited analysis.
    """
    analyzer = UnifiedCharacterAnalyzer(
        strategy=ChunkingStrategy.RATE_LIMITED,
        provider=provider,
        model=model,
        verbose=verbose
    )
    return analyzer.analyze(book_data)