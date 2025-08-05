"""
Unified transformation module that integrates character analysis and quality control.
This replaces the fragmented workflow with a single, cohesive transformation pipeline.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from api_client import UnifiedLLMClient
from .quality_control import quality_control_loop, validate_transformation
from .transform import transform_chapter
from .chunking import smart_chunk_sentences, estimate_tokens
from .chunking.model_configs import calculate_optimal_chunk_size, get_model_config

# Progress indicators
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'


class UnifiedBookTransformer:
    """
    Unified transformer that handles the complete pipeline:
    1. Character analysis (mandatory)
    2. Gender transformation
    3. Quality control
    4. Validation and reporting
    """
    
    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        """Initialize the unified transformer."""
        self.provider = provider
        self.model = model
        self.client = UnifiedLLMClient(provider)
        
    def transform_book_with_qc(self, 
                              book_data: Dict[str, Any],
                              transform_type: str = "gender_swap",
                              verbose: bool = True,
                              output_path: Optional[str] = None,
                              dry_run: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Transform a book with integrated quality control.
        Always uses maximum quality (3 QC iterations).
        
        Args:
            book_data: Parsed JSON book data
            transform_type: Type of transformation (all_male, all_female, gender_swap)
            verbose: Print progress information
            output_path: Optional path to save both JSON and text output
            dry_run: If True, only process first chapter
            
        Returns:
            Tuple of (transformed_book_data, transformation_report)
        """
        
        start_time = time.time()
        report = {
            'start_time': datetime.now().isoformat(),
            'transform_type': transform_type,
            'stages': {}
        }
        
        if verbose:
            print(f"\n{CYAN}{'='*60}{RESET}")
            print(f"{CYAN}Starting Unified Transformation Pipeline{RESET}")
            print(f"{CYAN}{'='*60}{RESET}")
            print(f"📖 Book: {book_data.get('title', 'Unknown')}")
            print(f"🔄 Transform: {transform_type}")
            print()
        
        # Stage 1: Character Analysis (MANDATORY)
        if verbose:
            print(f"{BOLD}Stage 1: Character Analysis{RESET}")
        
        character_start = time.time()
        try:
            from book_characters import analyze_book_characters
            characters, character_context = analyze_book_characters(
                book_data, 
                model=self.model, 
                provider=self.provider, 
                verbose=verbose
            )
            
            if not characters:
                raise ValueError("No characters found in book")
                
            report['stages']['character_analysis'] = {
                'success': True,
                'characters_found': len(characters),
                'time_taken': time.time() - character_start
            }
            
            if verbose:
                print(f"  ✓ Found {len(characters)} characters")
            
            # Save character analysis immediately
            try:
                import os
                from book_characters.exporter import save_character_analysis
                
                # Save characters to a file immediately
                if output_path:
                    char_dir = os.path.dirname(output_path)
                    char_filename = os.path.basename(output_path).replace('.json', '_characters.json')
                    char_path = os.path.join(char_dir, char_filename)
                    
                    metadata = {
                        "book_title": book_data.get('metadata', {}).get('title', 'Unknown'),
                        "total_characters": len(characters),
                        "provider": self.provider,
                        "model": self.model
                    }
                    
                    save_character_analysis(characters, char_path, metadata)
                    if verbose:
                        print(f"  💾 Character analysis saved to: {char_path}")
            except Exception as save_error:
                if verbose:
                    print(f"  ⚠️  Warning: Could not save character analysis: {save_error}")
                
        except Exception as e:
            report['stages']['character_analysis'] = {
                'success': False,
                'error': str(e),
                'time_taken': time.time() - character_start
            }
            
            # Character analysis is always mandatory
            raise RuntimeError(f"Character analysis failed: {e}")
        
        # Stage 2: Initial Transformation
        if verbose:
            print(f"\n{BOLD}Stage 2: Initial Transformation{RESET}")
        
        transform_start = time.time()
        transformed_chapters = []
        all_changes = []
        
        # In dry run mode, only process first chapter
        chapters_to_process = book_data['chapters'][:1] if dry_run else book_data['chapters']
        
        for idx, chapter in enumerate(chapters_to_process):
            if verbose:
                if dry_run:
                    print(f"  Chapter {idx + 1}/{len(chapters_to_process)} (DRY RUN - first chapter only)", end='', flush=True)
                else:
                    print(f"  Chapter {idx + 1}/{len(chapters_to_process)}", end='', flush=True)
            
            transformed_chapter, chapter_changes = transform_chapter(
                chapter,
                transform_type,
                character_context,
                model=self.model,
                provider=self.provider,
                verbose=False  # Suppress per-chapter output
            )
            
            transformed_chapters.append(transformed_chapter)
            all_changes.extend(chapter_changes)
            
            if verbose:
                print(f" ✓ ({len(chapter_changes)} changes)")
        
        report['stages']['initial_transform'] = {
            'success': True,
            'chapters_processed': len(transformed_chapters),
            'total_changes': len(all_changes),
            'time_taken': time.time() - transform_start
        }
        
        # Create initial transformed book
        transformed_book = book_data.copy()
        if dry_run:
            # In dry run, append untransformed chapters
            transformed_book['chapters'] = transformed_chapters + book_data['chapters'][1:]
        else:
            transformed_book['chapters'] = transformed_chapters
        
        # Stage 3: Quality Control (always run unless dry run)
        if not dry_run:
            if verbose:
                print(f"\n{BOLD}Stage 3: Quality Control{RESET}")
            
            qc_start = time.time()
            qc_changes_total = 0
            
            # Convert to text for QC
            from book_parser import recreate_text_from_json
            transformed_text = recreate_text_from_json(transformed_book)
            
            # Run quality control (always 3 iterations)
            cleaned_text, qc_changes = quality_control_loop(
                transformed_text,
                transform_type,
                model=self.model,
                provider=self.provider,
                max_iterations=3,
                verbose=verbose
            )
            
            qc_changes_total = len(qc_changes)
            
            # If QC made changes, update the book data
            if qc_changes:
                # This is simplified - in reality we'd need to map changes back to JSON structure
                # For now, store the QC'd text separately
                transformed_book['qc_text'] = cleaned_text
            
            report['stages']['quality_control'] = {
                'success': True,
                'issues_fixed': qc_changes_total,
                'iterations': 3,
                'time_taken': time.time() - qc_start
            }
        
        # Stage 4: Validation
        if verbose:
            print(f"\n{BOLD}Stage 4: Validation{RESET}")
        
        val_start = time.time()
        
        # Get original text for comparison
        from book_parser import recreate_text_from_json
        original_text = recreate_text_from_json(book_data)
        final_text = transformed_book.get('qc_text', recreate_text_from_json(transformed_book))
        
        validation_report = validate_transformation(
            original_text,
            final_text,
            transform_type,
            characters
        )
        
        report['stages']['validation'] = {
            'success': True,
            'quality_score': validation_report['quality_score'],
            'remaining_issues': validation_report['total_issues'],
            'time_taken': time.time() - val_start
        }
        
        if verbose:
            print(f"  Quality Score: {validation_report['quality_score']}/100")
            print(f"  Remaining Issues: {validation_report['total_issues']}")
        
        # Add metadata to transformed book
        transformed_book['transformation'] = {
            'type': transform_type,
            'model': self.model,
            'provider': self.provider,
            'timestamp': datetime.now().isoformat(),
            'quality_level': quality_level,
            'total_changes': len(all_changes) + qc_changes_total if quality_level != "fast" else len(all_changes),
            'character_analysis': characters,
            'validation': validation_report
        }
        
        # Stage 5: Output Generation
        if output_path:
            if verbose:
                print(f"\n{BOLD}Stage 5: Saving Output{RESET}")
            
            output_path = Path(output_path)
            
            # Save JSON
            json_path = output_path.with_suffix('.json')
            from book_parser import save_book_json
            save_book_json(transformed_book, str(json_path))
            
            # Save text
            text_path = output_path.with_suffix('.txt')
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(final_text)
            
            if verbose:
                print(f"  ✓ JSON saved to: {json_path}")
                print(f"  ✓ Text saved to: {text_path}")
        
        # Complete report
        total_time = time.time() - start_time
        report['total_time'] = total_time
        report['success'] = True
        
        if verbose:
            print(f"\n{GREEN}{'='*60}{RESET}")
            print(f"{GREEN}✓ Transformation Complete!{RESET}")
            print(f"{GREEN}{'='*60}{RESET}")
            print(f"⏱️  Total time: {total_time:.1f}s")
            print(f"📊 Quality score: {validation_report['quality_score']}/100")
            print(f"✏️  Total changes: {transformed_book['transformation']['total_changes']}")
        
        return transformed_book, report


def transform_book_unified(book_data: Dict[str, Any],
                         transform_type: str = "gender_swap",
                         model: Optional[str] = None,
                         provider: Optional[str] = None,
                         output_path: Optional[str] = None,
                         verbose: bool = True,
                         dry_run: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Convenience function for unified book transformation.
    
    This is the main entry point that should be used for all transformations.
    """
    transformer = UnifiedBookTransformer(provider=provider or "openai", model=model)
    return transformer.transform_book_with_qc(
        book_data=book_data,
        transform_type=transform_type,
        verbose=verbose,
        output_path=output_path,
        dry_run=dry_run
    )