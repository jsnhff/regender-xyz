"""
Parallel Book Transformation

This module adds parallel processing capabilities to speed up
book transformation by processing multiple chapters concurrently.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from api_client import UnifiedLLMClient
from book_transform.book_transformer import BookTransformer, TransformationResult


class AsyncLLMClient:
    """Async wrapper for LLM clients."""
    
    def __init__(self, client: UnifiedLLMClient, max_workers: int = 5):
        """
        Initialize async client.
        
        Args:
            client: Synchronous LLM client
            max_workers: Maximum concurrent workers
        """
        self.client = client
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def complete_async(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """Async completion using thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.client.complete,
            messages,
            **kwargs
        )
    
    def cleanup(self):
        """Cleanup executor."""
        self.executor.shutdown(wait=True)


class ParallelBookTransformer:
    """
    Book transformer with parallel chapter processing.
    
    This class processes multiple chapters concurrently for
    significant performance improvements on multi-chapter books.
    """
    
    def __init__(self,
                 provider: Optional[str] = None,
                 model: Optional[str] = None,
                 max_concurrent: int = 5,
                 verbose: bool = True):
        """
        Initialize parallel transformer.
        
        Args:
            provider: LLM provider
            model: Model name
            max_concurrent: Maximum concurrent chapter processing
            verbose: Whether to print progress
        """
        self.provider = provider
        self.model = model
        self.max_concurrent = max_concurrent
        self.verbose = verbose
        
        # Create base transformer for single-chapter processing
        self.base_transformer = BookTransformer(provider, model, verbose=False)
        
        # Create async client
        self.client = UnifiedLLMClient(provider=provider)
        self.async_client = AsyncLLMClient(self.client, max_concurrent)
    
    async def transform_book_async(self,
                                  book_data: Dict[str, Any],
                                  characters: Dict[str, Any],
                                  character_context: str,
                                  transform_type: str,
                                  dry_run: bool = False) -> TransformationResult:
        """
        Transform book using parallel processing.
        
        Args:
            book_data: Book data
            characters: Character analysis
            character_context: Character context
            transform_type: Transformation type
            dry_run: Whether to do dry run
            
        Returns:
            TransformationResult
        """
        start_time = time.time()
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Starting PARALLEL {transform_type} transformation")
            print(f"Max concurrent chapters: {self.max_concurrent}")
            print(f"{'='*60}")
        
        # Get chapters to process
        chapters = book_data.get('chapters', [])
        if dry_run:
            chapters = chapters[:1]
            if self.verbose:
                print("DRY RUN: Processing only first chapter")
        
        # Determine if parallel processing is beneficial
        use_parallel = len(chapters) > 2 and not dry_run
        
        if use_parallel:
            # Process chapters in parallel
            transformed_chapters, total_changes = await self._process_chapters_parallel(
                chapters=chapters,
                characters=characters,
                character_context=character_context,
                transform_type=transform_type
            )
        else:
            # Use sequential processing for small books
            if self.verbose:
                print("Using sequential processing (small book)")
            transformed_chapters = []
            total_changes = 0
            
            for chapter in chapters:
                transformed, changes = await self._transform_chapter_async(
                    chapter=chapter,
                    characters=characters,
                    character_context=character_context,
                    transform_type=transform_type,
                    chapter_num=1,
                    total_chapters=len(chapters)
                )
                transformed_chapters.append(transformed)
                total_changes += len(changes)
        
        # Create transformed book
        transformed_book = book_data.copy()
        transformed_book['chapters'] = transformed_chapters
        transformed_book['transformation'] = {
            'type': transform_type,
            'timestamp': datetime.now().isoformat(),
            'total_changes': total_changes,
            'dry_run': dry_run,
            'parallel_processing': use_parallel
        }
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Transformation complete!")
            print(f"Total changes: {total_changes}")
            print(f"Time: {processing_time:.1f}s")
            if use_parallel:
                sequential_estimate = len(chapters) * (processing_time / self.max_concurrent)
                speedup = sequential_estimate / processing_time
                print(f"Estimated speedup: {speedup:.1f}x")
            print(f"{'='*60}")
        
        return TransformationResult(
            transformed_book=transformed_book,
            characters_used=characters,
            transform_type=transform_type,
            total_changes=total_changes,
            processing_time=processing_time,
            metadata={
                'provider': self.provider,
                'model': self.model,
                'dry_run': dry_run,
                'parallel': use_parallel,
                'max_concurrent': self.max_concurrent
            }
        )
    
    async def _process_chapters_parallel(self,
                                        chapters: List[Dict[str, Any]],
                                        characters: Dict[str, Any],
                                        character_context: str,
                                        transform_type: str) -> Tuple[List[Dict], int]:
        """
        Process multiple chapters in parallel.
        
        Returns:
            Tuple of (transformed_chapters, total_changes)
        """
        if self.verbose:
            print(f"\nProcessing {len(chapters)} chapters in parallel...")
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Create tasks for all chapters
        tasks = []
        for i, chapter in enumerate(chapters):
            task = self._transform_with_limit(
                chapter=chapter,
                characters=characters,
                character_context=character_context,
                transform_type=transform_type,
                chapter_num=i + 1,
                total_chapters=len(chapters),
                semaphore=semaphore
            )
            tasks.append(task)
        
        # Process all tasks
        results = await asyncio.gather(*tasks)
        
        # Separate chapters and changes
        transformed_chapters = []
        total_changes = 0
        
        for transformed_chapter, changes in results:
            transformed_chapters.append(transformed_chapter)
            total_changes += len(changes)
        
        return transformed_chapters, total_changes
    
    async def _transform_with_limit(self,
                                   chapter: Dict[str, Any],
                                   characters: Dict[str, Any],
                                   character_context: str,
                                   transform_type: str,
                                   chapter_num: int,
                                   total_chapters: int,
                                   semaphore: asyncio.Semaphore) -> Tuple[Dict, List]:
        """Transform chapter with concurrency limit."""
        async with semaphore:
            return await self._transform_chapter_async(
                chapter=chapter,
                characters=characters,
                character_context=character_context,
                transform_type=transform_type,
                chapter_num=chapter_num,
                total_chapters=total_chapters
            )
    
    async def _transform_chapter_async(self,
                                      chapter: Dict[str, Any],
                                      characters: Dict[str, Any],
                                      character_context: str,
                                      transform_type: str,
                                      chapter_num: int,
                                      total_chapters: int) -> Tuple[Dict, List]:
        """Transform a single chapter asynchronously."""
        if self.verbose:
            print(f"  Chapter {chapter_num}/{total_chapters}: Starting...", end='', flush=True)
        
        start_time = time.time()
        
        # Use the base transformer's logic but with async client
        # For now, we'll run it in executor (future: make fully async)
        loop = asyncio.get_event_loop()
        transformed_chapter, changes = await loop.run_in_executor(
            None,
            self.base_transformer._transform_chapter,
            chapter,
            characters,
            character_context,
            transform_type
        )
        
        elapsed = time.time() - start_time
        
        if self.verbose:
            print(f"\r  Chapter {chapter_num}/{total_chapters}: ✓ ({len(changes)} changes, {elapsed:.1f}s)")
        
        return transformed_chapter, changes
    
    def transform_book(self,
                      book_data: Dict[str, Any],
                      characters: Dict[str, Any],
                      character_context: str,
                      transform_type: str,
                      dry_run: bool = False) -> TransformationResult:
        """
        Synchronous wrapper for async transformation.
        
        This allows the parallel transformer to be used in
        non-async code.
        """
        # Run async function in new event loop
        result = asyncio.run(self.transform_book_async(
            book_data=book_data,
            characters=characters,
            character_context=character_context,
            transform_type=transform_type,
            dry_run=dry_run
        ))
        
        # Cleanup
        self.async_client.cleanup()
        
        return result


def transform_book_parallel(book_data: Dict[str, Any],
                           transform_type: str,
                           characters: Optional[Dict[str, Any]] = None,
                           model: Optional[str] = None,
                           provider: Optional[str] = None,
                           max_concurrent: int = 5,
                           verbose: bool = True) -> Dict[str, Any]:
    """
    Transform book using parallel processing.
    
    This is a convenience function for using parallel transformation.
    """
    # If characters not provided, analyze them
    if characters is None:
        from book_characters import analyze_book_characters
        characters, character_context = analyze_book_characters(
            book_data, model=model, provider=provider, verbose=verbose
        )
    else:
        from book_characters import create_character_context
        character_context = create_character_context(characters)
    
    # Use parallel transformer
    transformer = ParallelBookTransformer(
        provider=provider,
        model=model,
        max_concurrent=max_concurrent,
        verbose=verbose
    )
    
    result = transformer.transform_book(
        book_data=book_data,
        characters=characters,
        character_context=character_context,
        transform_type=transform_type,
        dry_run=False
    )
    
    return result.transformed_book