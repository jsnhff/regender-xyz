"""
JSON-based book transformation module.

Processes pre-cleaned JSON books chapter by chapter,
applying gender transformations to each sentence.
"""

import json
from typing import Dict, Any, List, Tuple, Optional
import os
import sys
from datetime import datetime
import time

# Import OpenAI through utils
from utils import get_openai_client

# Import the existing gender transformation logic  
from gender_transform import transform_gender_with_context
from analyze_characters import analyze_characters

# Progress indicators
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'


def get_full_text_from_json(book_data: Dict[str, Any]) -> str:
    """Extract full text from JSON book for character analysis."""
    full_text = []
    
    for chapter in book_data['chapters']:
        # Add chapter title
        full_text.append(chapter['title'])
        # Add all sentences
        full_text.extend(chapter['sentences'])
    
    return '\n'.join(full_text)


def create_character_context(characters: Dict[str, Any]) -> str:
    """Create a character context string for transformations."""
    if not characters:
        return ""
    
    context_parts = []
    for char_name, char_info in characters.items():
        gender = char_info.get('gender', 'unknown')
        role = char_info.get('role', 'character')
        context_parts.append(f"- {char_name}: {gender}, {role}")
    
    return "Character Context:\n" + '\n'.join(context_parts)


def transform_sentences_chunk(
    sentences: List[str],
    transform_type: str,
    character_context: str,
    model: str = "gpt-4o-mini"
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Transform a chunk of sentences."""
    # Join sentences with clear markers
    text_chunk = '\n'.join([f"[{i}] {sent}" for i, sent in enumerate(sentences)])
    
    # Create transformation prompt
    transform_prompt = f"""Transform the following text according to these rules:

Gender Transformation Type: {transform_type}

{character_context}

Rules:
1. Transform all gender markers according to the {transform_type} transformation
2. Maintain the exact structure with [N] markers
3. Each sentence must remain on its own line
4. Preserve all punctuation and formatting
5. Track all changes made

Text to transform:
{text_chunk}

Return the transformed text with the same [N] markers."""

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a precise text transformation assistant. Follow the transformation rules exactly."},
                {"role": "user", "content": transform_prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        transformed_text = response.choices[0].message.content.strip()
        
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


def transform_chapter(
    chapter: Dict[str, Any],
    transform_type: str,
    character_context: str,
    model: str = "gpt-4o-mini",
    sentences_per_chunk: int = 50,
    verbose: bool = True
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Transform a single chapter."""
    sentences = chapter['sentences']
    total_sentences = len(sentences)
    
    if verbose:
        print(f"  Processing {chapter['title']} ({total_sentences} sentences)...")
    
    transformed_sentences = []
    all_changes = []
    
    # Process in chunks
    for i in range(0, total_sentences, sentences_per_chunk):
        chunk_end = min(i + sentences_per_chunk, total_sentences)
        chunk = sentences[i:chunk_end]
        
        if verbose:
            print(f"    Chunk {i//sentences_per_chunk + 1}/{(total_sentences + sentences_per_chunk - 1)//sentences_per_chunk}", end='', flush=True)
        
        # Transform the chunk
        transformed_chunk, changes = transform_sentences_chunk(
            chunk, transform_type, character_context, model
        )
        
        # Adjust change indices to be chapter-relative
        for change in changes:
            change['sentence_index'] += i
            change['chapter'] = chapter['number']
        
        transformed_sentences.extend(transformed_chunk)
        all_changes.extend(changes)
        
        if verbose:
            print(f" ... {len(changes)} changes")
        
        # Small delay to avoid rate limits
        time.sleep(0.1)
    
    # Create transformed chapter
    transformed_chapter = chapter.copy()
    transformed_chapter['sentences'] = transformed_sentences
    transformed_chapter['changes'] = len(all_changes)
    
    # Update word count (approximate)
    transformed_chapter['word_count'] = sum(len(sent.split()) for sent in transformed_sentences)
    
    return transformed_chapter, all_changes


def transform_json_book(
    book_data: Dict[str, Any],
    transform_type: str,
    model: str = "gpt-4o-mini",
    verbose: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Transform an entire book in JSON format, chapter by chapter."""
    start_time = time.time()
    
    # Step 1: Analyze characters from full text
    if verbose:
        print(f"\n{CYAN}Analyzing characters...{RESET}")
    
    full_text = get_full_text_from_json(book_data)
    
    # For large texts, we might want to sample for character analysis
    # to avoid token limits
    sample_size = 50000  # characters
    if len(full_text) > sample_size:
        # Take beginning, middle, and end samples
        text_sample = (
            full_text[:sample_size//3] + 
            full_text[len(full_text)//2 - sample_size//6:len(full_text)//2 + sample_size//6] +
            full_text[-sample_size//3:]
        )
    else:
        text_sample = full_text
    
    try:
        character_analysis = analyze_characters(text_sample, model=model)
        characters = character_analysis.get('characters', {})
        character_context = create_character_context(characters)
        
        if verbose:
            print(f"  Found {len(characters)} characters")
            if characters:
                print(f"  Main characters: {', '.join(list(characters.keys())[:5])}")
    except Exception as e:
        print(f"{YELLOW}Warning: Character analysis failed: {e}{RESET}")
        print(f"{YELLOW}Proceeding without character context{RESET}")
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
            verbose=verbose
        )
        
        transformed_chapters.append(transformed_chapter)
        all_changes.extend(chapter_changes)
    
    # Step 3: Create output JSON
    transformed_book = {
        'metadata': book_data['metadata'].copy(),
        'chapters': transformed_chapters,
        'statistics': {
            'total_chapters': len(transformed_chapters),
            'total_sentences': sum(ch['sentence_count'] for ch in transformed_chapters),
            'total_words': sum(ch['word_count'] for ch in transformed_chapters),
            'total_changes': len(all_changes),
            'processing_time': f"{time.time() - start_time:.1f}s"
        },
        'transformation': {
            'type': transform_type,
            'model': model,
            'timestamp': datetime.now().isoformat(),
            'character_context': character_context,
            'changes': all_changes if len(all_changes) < 100 else all_changes[:100]  # Limit stored changes
        }
    }
    
    # Update format version
    transformed_book['metadata']['format_version'] = '2.0'
    
    return transformed_book