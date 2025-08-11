"""
Unified Book Transformer Class

This module consolidates all transformation logic into a single,
well-organized class, replacing the scattered functions across
transform.py, llm_transform.py, and unified_transform.py.
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from api_client import UnifiedLLMClient
from book_transform.chunking.token_utils import smart_chunk_sentences, estimate_tokens
from book_transform.prompt_templates import get_prompt


@dataclass
class TransformationResult:
    """Result of a book transformation."""
    transformed_book: Dict[str, Any]
    characters_used: Dict[str, Any]
    transform_type: str
    total_changes: int
    processing_time: float
    quality_score: Optional[float] = None
    qc_iterations: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BookTransformer:
    """
    Core transformation engine for gender transformation.
    
    This class consolidates all transformation logic into a single,
    well-tested interface.
    """
    
    def __init__(self,
                 provider: Optional[str] = None,
                 model: Optional[str] = None,
                 verbose: bool = True):
        """
        Initialize the book transformer.
        
        Args:
            provider: LLM provider to use
            model: Model name
            verbose: Whether to print progress
        """
        self.provider = provider
        self.model = model
        self.verbose = verbose
        self.client = UnifiedLLMClient(provider=provider)
    
    def transform_book(self,
                      book_data: Dict[str, Any],
                      characters: Dict[str, Any],
                      character_context: str,
                      transform_type: str,
                      dry_run: bool = False) -> TransformationResult:
        """
        Transform a book's gender representation.
        
        Args:
            book_data: Book data dictionary
            characters: Character analysis results
            character_context: Character context string
            transform_type: Type of transformation (all_male, all_female, gender_swap)
            dry_run: If True, only transform first chapter
            
        Returns:
            TransformationResult with all transformation data
        """
        start_time = time.time()
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Starting {transform_type} transformation")
            print(f"{'='*60}")
        
        # Initialize result
        transformed_chapters = []
        total_changes = 0
        
        # Get chapters to process
        chapters = book_data.get('chapters', [])
        if dry_run:
            chapters = chapters[:1]  # Only first chapter for dry run
            if self.verbose:
                print("DRY RUN: Processing only first chapter")
        
        # Transform each chapter
        for i, chapter in enumerate(chapters):
            if self.verbose:
                print(f"\nChapter {i+1}/{len(chapters)}: {chapter.get('title', 'Untitled')}")
            
            transformed_chapter, chapter_changes = self._transform_chapter(
                chapter=chapter,
                characters=characters,
                character_context=character_context,
                transform_type=transform_type
            )
            
            transformed_chapters.append(transformed_chapter)
            total_changes += len(chapter_changes)
            
            if self.verbose:
                print(f"  ✓ {len(chapter_changes)} changes made")
        
        # Create transformed book
        transformed_book = book_data.copy()
        transformed_book['chapters'] = transformed_chapters
        transformed_book['transformation'] = {
            'type': transform_type,
            'timestamp': datetime.now().isoformat(),
            'total_changes': total_changes,
            'dry_run': dry_run
        }
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Transformation complete!")
            print(f"Total changes: {total_changes}")
            print(f"Time: {processing_time:.1f}s")
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
                'dry_run': dry_run
            }
        )
    
    def _transform_chapter(self,
                          chapter: Dict[str, Any],
                          characters: Dict[str, Any],
                          character_context: str,
                          transform_type: str) -> Tuple[Dict[str, Any], List[Dict]]:
        """
        Transform a single chapter.
        
        Returns:
            Tuple of (transformed_chapter, list_of_changes)
        """
        # Extract sentences from chapter
        sentences = []
        paragraph_boundaries = []
        
        for para_idx, paragraph in enumerate(chapter.get('paragraphs', [])):
            para_sentences = paragraph.get('sentences', [])
            sentences.extend(para_sentences)
            paragraph_boundaries.append(len(sentences))
        
        if not sentences:
            return chapter.copy(), []
        
        # Chunk sentences for processing
        chunks = smart_chunk_sentences(
            sentences=sentences,
            model=self.model,
            character_context=character_context,
            transform_type=transform_type,
            verbose=False
        )
        
        # Process chunks
        transformed_sentences = []
        all_changes = []
        
        for chunk_idx, chunk in enumerate(chunks):
            if self.verbose:
                print(f"  Processing chunk {chunk_idx+1}/{len(chunks)}...", end='', flush=True)
            
            try:
                transformed_chunk, changes = self._transform_chunk(
                    sentences=chunk,
                    transform_type=transform_type,
                    character_context=character_context
                )
                
                transformed_sentences.extend(transformed_chunk)
                all_changes.extend(changes)
                
                if self.verbose:
                    print(f" ✓")
                
                # Clear memory
                del transformed_chunk
                del changes
                
            except Exception as e:
                if self.verbose:
                    print(f" ❌ Error: {e}")
                raise
        
        # Rebuild chapter with transformed sentences
        transformed_chapter = chapter.copy()
        transformed_paragraphs = []
        
        sentence_idx = 0
        for para_boundary in paragraph_boundaries:
            para_sentences = transformed_sentences[sentence_idx:para_boundary]
            if para_sentences:
                transformed_paragraphs.append({'sentences': para_sentences})
            sentence_idx = para_boundary
        
        transformed_chapter['paragraphs'] = transformed_paragraphs
        
        return transformed_chapter, all_changes
    
    def _transform_chunk(self,
                        sentences: List[str],
                        transform_type: str,
                        character_context: str) -> Tuple[List[str], List[Dict]]:
        """
        Transform a chunk of sentences using LLM.
        
        Returns:
            Tuple of (transformed_sentences, changes_made)
        """
        # Create numbered format for LLM
        numbered_sentences = []
        for i, sent in enumerate(sentences):
            numbered_sentences.append(f"[{i}] {sent}")
        
        sentences_text = '\n'.join(numbered_sentences)
        
        # Get transformation prompt
        prompts = get_prompt(
            prompt_type="transform",
            model_name=self.model,
            provider=self.provider,
            text=sentences_text,
            transform_type=transform_type,
            character_context=character_context
        )
        system_prompt = prompts.get("system", "")
        user_prompt = prompts.get("user", "")
        
        # Call LLM
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
        
        # Parse response
        try:
            result = json.loads(response.content)
            transformed_sentences = result.get('sentences', sentences)
            changes = result.get('changes', [])
            
            # Ensure we have the right number of sentences
            if len(transformed_sentences) != len(sentences):
                print(f"Warning: Expected {len(sentences)} sentences, got {len(transformed_sentences)}")
                transformed_sentences = sentences  # Fallback to original
                changes = []
            
            return transformed_sentences, changes
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return sentences, []  # Return original on error


class UnifiedBookTransformer:
    """
    High-level transformer with quality control integration.
    
    This wraps BookTransformer and adds quality control, validation,
    and other pipeline features.
    """
    
    def __init__(self,
                 provider: Optional[str] = None,
                 model: Optional[str] = None,
                 quality_level: str = "standard",
                 verbose: bool = True):
        """
        Initialize unified transformer.
        
        Args:
            provider: LLM provider
            model: Model name
            quality_level: Quality control level (basic, standard, high)
            verbose: Whether to print progress
        """
        self.transformer = BookTransformer(provider, model, verbose)
        self.quality_level = quality_level
        self.verbose = verbose
    
    def transform_with_qc(self,
                         book_data: Dict[str, Any],
                         characters: Dict[str, Any],
                         character_context: str,
                         transform_type: str,
                         dry_run: bool = False) -> TransformationResult:
        """
        Transform book with quality control.
        
        Args:
            book_data: Book data
            characters: Character analysis
            character_context: Character context
            transform_type: Transformation type
            dry_run: Whether to do dry run
            
        Returns:
            TransformationResult with QC applied
        """
        # Initial transformation
        result = self.transformer.transform_book(
            book_data=book_data,
            characters=characters,
            character_context=character_context,
            transform_type=transform_type,
            dry_run=dry_run
        )
        
        # Apply quality control if not dry run
        if not dry_run and self.quality_level != "none":
            result = self._apply_quality_control(result, transform_type)
        
        return result
    
    def _apply_quality_control(self,
                              result: TransformationResult,
                              transform_type: str) -> TransformationResult:
        """Apply quality control to transformation result."""
        if self.verbose:
            print("\nApplying quality control...")
        
        # Import QC module
        from book_transform.quality_control import quality_control_loop, validate_transformation
        
        # Convert book to text for QC
        from book_parser.utils.recreate_text import recreate_text_generator
        text_lines = list(recreate_text_generator(result.transformed_book))
        text = ''.join(text_lines)
        
        # Run QC
        qc_iterations = 1 if self.quality_level == "standard" else 3
        
        cleaned_text, qc_changes = quality_control_loop(
            text=text,
            transform_type=transform_type,
            model=self.transformer.model,
            provider=self.transformer.provider,
            max_iterations=qc_iterations,
            verbose=self.verbose
        )
        
        # Validate
        quality_score = validate_transformation(
            original_text="",  # Not needed for scoring
            transformed_text=cleaned_text,
            transform_type=transform_type,
            verbose=False
        )
        
        # Update result
        result.qc_iterations = qc_iterations
        result.quality_score = quality_score['overall_score']
        result.metadata['qc_changes'] = len(qc_changes)
        
        if self.verbose:
            print(f"  Quality score: {quality_score['overall_score']}/100")
            print(f"  QC changes: {len(qc_changes)}")
        
        return result


# Backward compatibility function
def transform_book(book_data: Dict[str, Any],
                   transform_type: str,
                   characters: Optional[Dict[str, Any]] = None,
                   model: Optional[str] = None,
                   provider: Optional[str] = None,
                   verbose: bool = True) -> Dict[str, Any]:
    """
    Backward compatibility wrapper for the old transform_book function.
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
    
    # Use new transformer
    transformer = BookTransformer(provider=provider, model=model, verbose=verbose)
    result = transformer.transform_book(
        book_data=book_data,
        characters=characters,
        character_context=character_context,
        transform_type=transform_type,
        dry_run=False
    )
    
    return result.transformed_book