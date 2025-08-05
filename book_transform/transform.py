"""Main transformation module for gender transformation."""

import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from api_client import UnifiedLLMClient
# Import moved inside function to avoid circular import
from .chunking import smart_chunk_sentences, estimate_tokens
from .chunking.model_configs import calculate_optimal_chunk_size, get_model_config

# Import the transformation function
from .llm_transform import transform_gender_with_context

# Progress indicators
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'


class BookTransformer:
    """Main class for transforming books (gender and other narrative elements)."""
    
    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        """
        Initialize the transformer.
        
        Args:
            provider: AI provider to use
            model: Model to use for transformation
        """
        self.provider = provider
        self.model = model
        self.client = UnifiedLLMClient(provider)
    
    def transform_book(self, book_data: Dict[str, Any], 
                      transform_type: str = "gender_swap",
                      verbose: bool = True,
                      dry_run: bool = False) -> Dict[str, Any]:
        """
        Transform gender in a book.
        
        Args:
            book_data: JSON book data
            transform_type: Type of transformation
            verbose: Whether to print progress
            dry_run: If True, only process first chapter
            
        Returns:
            Transformed book data
        """
        return transform_book(
            book_data,
            transform_type=transform_type,
            model=self.model,
            provider=self.provider,
            verbose=verbose,
            dry_run=dry_run
        )
    
    def transform_sentences(self, sentences: List[str],
                          transform_type: str,
                          character_context: str = "") -> Tuple[List[str], List[Dict]]:
        """Transform a list of sentences."""
        return transform_sentences_chunk(
            sentences,
            transform_type,
            character_context,
            self.model
        )


def transform_sentences_chunk(sentences: List[str], 
                            transform_type: str,
                            character_context: str,
                            model: Optional[str] = None,
                            provider: Optional[str] = None) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Transform a chunk of sentences."""
    try:
        # Import the transformation function
        from .llm_transform import create_transformation_prompt, TRANSFORM_TYPES
        
        # Check if transform_type is valid
        if transform_type not in TRANSFORM_TYPES:
            raise ValueError(f"Invalid transform type: {transform_type}")
        
        # Create numbered sentences text
        numbered_text = ""
        for i, sentence in enumerate(sentences):
            numbered_text += f"[{i}] {sentence}\n"
        
        # Create the transformation prompt with explicit instructions
        prompt = create_transformation_prompt(
            text=numbered_text,
            transform_type=transform_type,
            character_context=character_context,
            json_output=False  # We want plain text for sentence processing
        )
        
        # Add specific instructions for numbered format
        prompt += f"""

IMPORTANT: Return the transformed sentences in the EXACT same numbered format:
[0] transformed first sentence
[1] transformed second sentence
[2] transformed third sentence
...and so on.

Keep the exact same number of sentences. Do not add or remove any sentences."""
        
        # Call AI
        client = UnifiedLLMClient(provider=provider)
        messages = [{"role": "user", "content": prompt}]
        response = client.complete(
            messages=messages,
            model=model,
            temperature=0.1
        )
        transformed_text = response.content.strip()
        
        # Parse the transformed sentences
        transformed_sentences = []
        changes = []
        
        for line in transformed_text.split('\n'):
            if line.strip() and line.strip()[0] == '[':
                # Extract sentence number and text
                try:
                    bracket_end = line.index(']')
                    sent_num = int(line[1:bracket_end])
                    sent_text = line[bracket_end + 1:].strip()
                    
                    # Check if changed
                    if sent_num < len(sentences) and sent_text != sentences[sent_num]:
                        changes.append({
                            'sentence_index': sent_num,
                            'original': sentences[sent_num],
                            'transformed': sent_text
                        })
                    
                    transformed_sentences.append(sent_text)
                except (ValueError, IndexError):
                    # If parsing fails, append the original sentence
                    transformed_sentences.append(line)
        
        # Ensure we have the right number of sentences
        if len(transformed_sentences) != len(sentences):
            print(f"{YELLOW}Warning: Sentence count mismatch. Expected {len(sentences)}, got {len(transformed_sentences)}{RESET}")
            # Pad or truncate as needed
            while len(transformed_sentences) < len(sentences):
                transformed_sentences.append(sentences[len(transformed_sentences)])
            transformed_sentences = transformed_sentences[:len(sentences)]
        
        return transformed_sentences, changes
        
    except Exception as e:
        print(f"{RED}Error in transformation: {e}{RESET}")
        # Return original sentences on error
        return sentences, []


def transform_chapter(chapter: Dict[str, Any],
                     transform_type: str,
                     character_context: str,
                     model: str = "gpt-4o-mini",
                     provider: Optional[str] = None,
                     sentences_per_chunk: Optional[int] = None,
                     verbose: bool = True) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Transform a single chapter with model-aware chunking."""
    # Handle both old (flat sentences) and new (paragraphs) structures
    if 'paragraphs' in chapter:
        # New structure - extract all sentences with paragraph tracking
        sentences = []
        sentence_to_paragraph = []  # Track which paragraph each sentence belongs to
        
        for para_idx, paragraph in enumerate(chapter['paragraphs']):
            for sent in paragraph.get('sentences', []):
                sentences.append(sent)
                sentence_to_paragraph.append(para_idx)
    else:
        # Old structure - flat sentences
        sentences = chapter.get('sentences', [])
        sentence_to_paragraph = [0] * len(sentences)
    
    total_sentences = len(sentences)
    
    # Calculate optimal chunk size if not specified
    if sentences_per_chunk is None:
        sentences_per_chunk = calculate_optimal_chunk_size(sentences, model)
        if verbose:
            config = get_model_config(model)
            print(f"    Using chunk size: {sentences_per_chunk} sentences (model: {model})")
    
    if verbose:
        print(f"  Processing {chapter['title']} ({total_sentences} sentences)...")
    
    transformed_sentences = []
    all_changes = []
    
    # Use smart token-based chunking
    chunks = smart_chunk_sentences(
        sentences, 
        model, 
        character_context,
        transform_type,
        verbose=False
    )
    
    if verbose:
        print(f"    Smart chunking: {len(chunks)} chunks for {total_sentences} sentences")
    
    # Process smart chunks
    sentence_index = 0
    for chunk_idx, chunk in enumerate(chunks):
        if verbose:
            chunk_tokens = sum(estimate_tokens(s) for s in chunk)
            print(f"    Chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk)} sentences, ~{chunk_tokens} tokens)", end='', flush=True)
        
        # Transform the chunk
        transformed_chunk, changes = transform_sentences_chunk(
            chunk, transform_type, character_context, model, provider
        )
        
        # Adjust change indices to be chapter-relative
        for change in changes:
            change['sentence_index'] += sentence_index
            change['chapter'] = chapter['number']
        
        transformed_sentences.extend(transformed_chunk)
        all_changes.extend(changes)
        sentence_index += len(chunk)
        
        if verbose:
            print(f" - {len(changes)} changes")
    
    # Create transformed chapter
    transformed_chapter = chapter.copy()
    
    # Reconstruct paragraph structure if present
    if 'paragraphs' in chapter:
        # Rebuild paragraphs with transformed sentences
        transformed_paragraphs = []
        current_para_idx = -1
        current_sentences = []
        
        for sent_idx, sent in enumerate(transformed_sentences):
            para_idx = sentence_to_paragraph[sent_idx]
            
            # If we've moved to a new paragraph, save the current one
            if para_idx != current_para_idx and current_para_idx >= 0:
                transformed_paragraphs.append({
                    'sentences': current_sentences
                })
                current_sentences = []
            
            # Add to current paragraph
            current_para_idx = para_idx
            current_sentences.append(sent)
        
        # Don't forget the last paragraph
        if current_para_idx >= 0:
            transformed_paragraphs.append({
                'sentences': current_sentences
            })
        
        transformed_chapter['paragraphs'] = transformed_paragraphs
    else:
        # Old structure - just use flat sentences
        transformed_chapter['sentences'] = transformed_sentences
    
    transformed_chapter['transformation_stats'] = {
        'total_changes': len(all_changes),
        'chunks_processed': len(chunks)
    }
    
    return transformed_chapter, all_changes


def transform_book(book_data: Dict[str, Any],
                  transform_type: str = "gender_swap",
                  model: str = "gpt-4o-mini",
                  provider: Optional[str] = None,
                  verbose: bool = True,
                  dry_run: bool = False) -> Dict[str, Any]:
    """
    Transform gender representation in a book.
    
    Args:
        book_data: JSON book data
        transform_type: Type of transformation
        model: Model to use
        verbose: Whether to print progress
        dry_run: If True, only process first chapter
        
    Returns:
        Transformed book data
    """
    start_time = time.time()
    
    # Step 1: Analyze characters
    try:
        from book_characters import analyze_book_characters
        characters, character_context = analyze_book_characters(
            book_data, model=model, provider=provider, verbose=verbose
        )
    except Exception as e:
        if verbose:
            print(f"Warning: Character analysis failed: {e}")
            print("Proceeding without character context")
        characters = {}
        character_context = ""
    
    # Step 2: Transform chapters
    transformed_chapters = []
    all_changes = []
    chapters_to_process = book_data['chapters'][:1] if dry_run else book_data['chapters']
    
    if verbose:
        print(f"\n{CYAN}Transforming {len(chapters_to_process)} chapters...{RESET}")
    
    for idx, chapter in enumerate(chapters_to_process):
        if verbose:
            print(f"\n{BOLD}Chapter {idx + 1}/{len(chapters_to_process)}{RESET}")
        
        transformed_chapter, chapter_changes = transform_chapter(
            chapter,
            transform_type,
            character_context,
            model=model,
            provider=provider,
            verbose=verbose
        )
        
        transformed_chapters.append(transformed_chapter)
        all_changes.extend(chapter_changes)
    
    # Create transformed book
    transformed_book = book_data.copy()
    transformed_book['chapters'] = transformed_chapters
    transformed_book['transformation'] = {
        'type': transform_type,
        'model': model,
        'timestamp': datetime.now().isoformat(),
        'total_changes': len(all_changes),
        'chapters_processed': len(transformed_chapters),
        'processing_time': time.time() - start_time,
        'character_analysis': characters
    }
    
    # Update statistics
    if 'statistics' in transformed_book:
        transformed_book['statistics']['transformation_changes'] = len(all_changes)
    
    # Add detailed changes if not too many
    if len(all_changes) < 1000:
        transformed_book['transformation']['detailed_changes'] = all_changes
    
    if verbose:
        print(f"\n{GREEN}✓ Transformation complete!{RESET}")
        print(f"  Total changes: {len(all_changes)}")
        print(f"  Time taken: {time.time() - start_time:.1f}s")
    
    return transformed_book