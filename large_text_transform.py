#!/usr/bin/env python3
"""
Module for transforming large texts like full novels.
Handles chunking, chapter identification, and maintaining consistency across chunks.
"""

import os
import sys
import json
import math
import time
import logging
import traceback
import re
from typing import Dict, List, Tuple, Any
from datetime import datetime
from collections import defaultdict

# Import local modules
import cli_visuals
from cli_visuals import Colors
from analyze_characters import analyze_characters
from gender_transform import transform_gender, transform_gender_with_context, TRANSFORM_TYPES
from utils import get_openai_client, load_text_file, save_text_file, APIError


class ColoredFormatter(logging.Formatter):
    """Custom formatter for logging with colors and better timestamp placement."""
    
    # ANSI color codes
    RESET = "\033[0m"
    WHITE = "\033[37m"        # White for regular text
    BRIGHT_WHITE = "\033[97m" # Bright white for emphasis
    BRIGHT_BLACK = "\033[90m"  # Dark gray for timestamps
    GREEN = "\033[32m"        # Green for INFO
    YELLOW = "\033[33m"       # Yellow for WARNING
    RED = "\033[31m"          # Red for ERROR
    BRIGHT_RED = "\033[91m"   # Bright red for CRITICAL
    BRIGHT_GREEN = "\033[92m" # Bright green for success
    CYAN = "\033[36m"         # Cyan for DEBUG
    
    # Format strings for different log levels
    FORMATS = {
        logging.DEBUG: CYAN + "✓ %(message)s" + RESET + BRIGHT_BLACK + " [%(asctime)s]" + RESET,
        logging.INFO: BRIGHT_BLACK + "✓ %(message)s" + RESET + BRIGHT_BLACK + " [%(asctime)s]" + RESET,
        logging.WARNING: YELLOW + "⚠ %(message)s" + RESET + BRIGHT_BLACK + " [%(asctime)s]" + RESET,
        logging.ERROR: RED + "✗ %(message)s" + RESET + BRIGHT_BLACK + " [%(asctime)s]" + RESET,
        logging.CRITICAL: BRIGHT_RED + "✗ %(message)s" + RESET + BRIGHT_BLACK + " [%(asctime)s]" + RESET
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)


class SpinnerAwareHandler(logging.StreamHandler):
    """Custom log handler that preserves spinner position."""
    
    def emit(self, record):
        try:
            # First output a carriage return to go to the beginning of the line
            # This ensures the log message doesn't break the spinner animation
            self.stream.write('\r')
            self.stream.write(' ' * 80)  # Clear the line
            self.stream.write('\r')
            msg = self.format(record)
            self.stream.write(msg)
            self.stream.write('\n')
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logging(log_dir="logs"):
    """Set up logging configuration with colored output and better timestamp placement.
    
    Args:
        log_dir: Directory to store log files
        
    Returns:
        Logger instance
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"transform_full_novel_{timestamp}.log")
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Create spinner-aware console handler with colored formatter
    console_handler = SpinnerAwareHandler()
    console_handler.setFormatter(ColoredFormatter())
    
    # Create file handler with standard formatter (no colors in log file)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


def identify_chapter_titles(text: str, model: str = "gpt-4.1-mini") -> List[Dict[str, Any]]:
    """Identify chapter titles in the text using AI with regex validation.
    
    Uses AI to identify chapter titles and their positions, then validates with regex.
    This allows for more flexible chapter title detection while maintaining accuracy.
    
    Args:
        text: The text to process
        model: The model to use for AI analysis
        
    Returns:
        List of dicts with chapter info including:
        - title: The chapter title
        - position: Position in text where title appears
        - length: Length of the chapter
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting AI-based chapter title identification...")
    
    system_prompt = """You are an expert at analyzing literary texts.
    Your task is to identify ALL chapter titles in the given text.
    
    Rules for chapter identification:
    1. Look for clear chapter markers like "Chapter X", "CHAPTER X", etc.
    2. Include the exact title as it appears in the text
    3. Note the character position where each title appears
    4. Distinguish between actual chapter titles and table of contents entries
    5. Handle variations in formatting (e.g., "Chapter I" vs "CHAPTER ONE")
    6. Be thorough - don't miss any chapters
    7. Ignore false positives like chapter mentions in the text body
    
    IMPORTANT: You must return a JSON array of objects, not a JSON object.
    Each object in the array should have:
    - title: The exact chapter title as it appears
    - position: Character position where it appears
    """
    
    user_prompt = f"""Please identify all chapter titles in this text.
    Return ONLY a JSON array of chapter title objects.
    Each object should have 'title' and 'position' fields.
    
    Example format:
    [
        {{"title": "Chapter I", "position": 1234}},
        {{"title": "CHAPTER II", "position": 5678}}
    ]
    
    Text to analyze:
    {text}"""
    
    try:
        # Get response from AI
        client = get_openai_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        
        # Parse AI response
        result = json.loads(response.choices[0].message.content)
        if not isinstance(result, list):
            logger.warning("AI response not in expected format")
            return []
            
        # Validate each identified title with regex
        title_patterns = [
            r"(?:Chapter|CHAPTER)\s+[IVXLCDMivxlcdm]+\.?",  # Roman numerals with optional period
            r"(?:Chapter|CHAPTER)\s+\d+\.?",                 # Arabic numerals with optional period
            r"(?:Chapter|CHAPTER)\s+[A-Za-z]+\.?",           # Spelled out numbers with optional period
            r"\[Illustration:\s*Chapter\s+[IVXLCDMivxlcdm]+\.?\]",  # Illustration markers with Roman numerals
            r"\[Illustration:\s*Chapter\s+\d+\.?\]",         # Illustration markers with Arabic numerals
            r"\[Illustration:\s*Chapter\s+[A-Za-z]+\.?\]"    # Illustration markers with spelled out numbers
        ]
        
        validated_chapters = []
        for chapter in result:
            title = chapter.get('title', '')
            position = chapter.get('position', -1)
            
            # Skip invalid entries
            if not title or position < 0:
                continue
                
            # Verify title exists at the specified position
            text_at_pos = text[max(0, position-20):position+len(title)+20]
            if title not in text_at_pos:
                logger.warning(f"Title '{title}' not found at specified position {position}")
                continue
                
            # Validate with regex patterns
            if any(re.match(pattern, title) for pattern in title_patterns):
                validated_chapters.append({
                    'title': title,
                    'position': position,
                    'length': 0  # Will be calculated later
                })
                logger.info(f"Validated title '{title}' at position {position}")
            else:
                logger.warning(f"Title '{title}' failed regex validation")
        
        # Sort chapters by position
        validated_chapters.sort(key=lambda x: x['position'])
        
        # Calculate chapter lengths
        for i in range(len(validated_chapters) - 1):
            validated_chapters[i]['length'] = validated_chapters[i + 1]['position'] - validated_chapters[i]['position']
        
        # Last chapter goes to end of text
        if validated_chapters:
            validated_chapters[-1]['length'] = len(text) - validated_chapters[-1]['position']
            
        # Log results
        logger.info(f"Found {len(validated_chapters)} validated chapters")
        for i, chapter in enumerate(validated_chapters[:5]):
            logger.info(f"Chapter {i+1}: {chapter['title']} - {chapter['length']} chars")
            
        return validated_chapters
        
    except Exception as e:
        logger.error(f"Error in chapter title identification: {e}")
        logger.error(traceback.format_exc())
        return []


def locate_chapter_boundaries(text: str, chapter_titles: List[str]) -> List[Tuple[int, int]]:
    """Locate the start and end positions of each chapter in the text.
    
    Args:
        text: The text to analyze
        chapter_titles: List of chapter titles to find
    
    Returns:
        List of (start, end) tuples for each chapter
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Searching for boundaries of {len(chapter_titles)} chapters")
    
    # Initialize boundaries list
    boundaries = []
    
    # Create a regex pattern that matches any of the chapter titles
    # Escape special characters in titles and join with OR operator
    escaped_titles = [re.escape(title) for title in chapter_titles]
    pattern = '|'.join(escaped_titles)
    
    # Find all matches of chapter titles
    matches = list(re.finditer(pattern, text))
    
    if not matches:
        logger.warning("No chapter titles found in text")
        return []
    
    # Create a mapping of title to all its positions
    title_positions = defaultdict(list)
    for match in matches:
        title = match.group(0)
        title_positions[title].append(match.start())
    
    # Log any titles that appear multiple times
    for title, positions in title_positions.items():
        if len(positions) > 1:
            logger.warning(f"Title '{title}' appears {len(positions)} times at positions {positions}")
    
    # Process each chapter
    for i, title in enumerate(chapter_titles):
        positions = title_positions.get(title, [])
        
        if not positions:
            logger.warning(f"Title not found in text: '{title}'")
            continue
            
        # Use the first occurrence if multiple exist
        start = positions[0]
        
        # End is either the start of the next chapter or the end of text
        end = len(text)
        if i < len(chapter_titles) - 1:
            next_title = chapter_titles[i + 1]
            next_positions = title_positions.get(next_title, [])
            if next_positions:
                end = next_positions[0]
        
        boundaries.append((start, end))
        logger.info(f"Chapter '{title}': {start} to {end} ({end - start} characters)")
    
    # Validate boundaries
    if boundaries:
        logger.info(f"Found {len(boundaries)} chapter boundaries")
        # Check for overlaps
        for i in range(len(boundaries) - 1):
            if boundaries[i][1] > boundaries[i + 1][0]:
                logger.warning(f"Overlap detected between chapters {i} and {i + 1}")
    else:
        logger.warning("No chapter boundaries found")
    
    return boundaries


def find_chapters_in_text(text: str, chapter_info: Dict[str, Any]) -> List[Dict]:
    """Find all chapters in the text using identified patterns.
    
    Args:
        text: The full text to analyze
        chapter_info: Dictionary with chapter pattern information
        
    Returns:
        List of dictionaries with chapter info
    """
    logger = logging.getLogger()
    logger.info("Finding chapters in text using patterns...")
    
    # Get patterns from the chapter info
    regex_patterns = chapter_info.get("regex_patterns", [])
    sample_matches = chapter_info.get("sample_matches", [])
    
    # If we have sample matches but no regex patterns, create patterns from the samples
    if not regex_patterns and sample_matches:
        import re
        regex_patterns = [re.escape(sample) for sample in sample_matches]
    
    # If we still don't have patterns, use default patterns for common chapter formats
    if not regex_patterns:
        logger.warning("No patterns found, using default chapter patterns")
        regex_patterns = [
            r"Chapter\s+[IVXLCDMivxlcdm]+\.?",  # Chapter I, Chapter II, etc.
            r"CHAPTER\s+[IVXLCDMivxlcdm]+\.?",  # CHAPTER I, CHAPTER II, etc.
            r"Chapter\s+\d+\.?",  # Chapter 1, Chapter 2, etc.
            r"CHAPTER\s+\d+\.?",  # CHAPTER 1, CHAPTER 2, etc.
            r"Chapter\s+[A-Za-z]+\.?",  # Chapter One, Chapter Two, etc.
            r"CHAPTER\s+[A-Za-z]+\.?"  # CHAPTER One, CHAPTER Two, etc.
        ]
    
    # Combine all patterns into one regex
    import re
    combined_pattern = "|".join(f"({pattern})" for pattern in regex_patterns)
    
    # Find all matches in the text
    matches = list(re.finditer(combined_pattern, text))
    
    if not matches:
        logger.warning(f"No chapter markers found using patterns: {regex_patterns}")
        # Fallback: try to find any chapter-like patterns
        fallback_pattern = r"(?:Chapter|CHAPTER)\s+.{1,10}"
        matches = list(re.finditer(fallback_pattern, text))
    
    if not matches:
        logger.warning("No chapter markers found. Using fallback chunking.")
        # Fallback: divide text into roughly equal chunks
        chunk_size = 10000  # 10K chars per chunk
        num_chunks = max(1, len(text) // chunk_size)
        chunk_size = len(text) // num_chunks
        
        chapters = []
        for i in range(num_chunks):
            start_idx = i * chunk_size
            end_idx = start_idx + chunk_size if i < num_chunks - 1 else len(text)
            chapters.append({
                "title": f"Section {i+1}",
                "start_index": start_idx,
                "end_index": end_idx
            })
        return chapters
    
    logger.info(f"Found {len(matches)} potential chapter markers")
    
    # Process each match to create chapter boundaries
    chapters = []
    for i, match in enumerate(matches):
        title = text[match.start():match.end()]
        start_index = match.start()
        
        # For all but the last chapter, end at the start of the next chapter
        if i < len(matches) - 1:
            end_index = matches[i + 1].start()
        else:
            end_index = len(text)
        
        chapters.append({
            "title": title,
            "start_index": start_index,
            "end_index": end_index
        })
    
    # Validate chapter sizes
    MIN_CHAPTER_SIZE = 1000  # Minimum chapter size in characters
    small_chapters = [i for i, ch in enumerate(chapters) if ch['end_index'] - ch['start_index'] < MIN_CHAPTER_SIZE]
    
    if small_chapters:
        logger.warning(f"Found {len(small_chapters)} chapters smaller than {MIN_CHAPTER_SIZE} characters")
        
        # Merge small chapters with the next chapter
        new_chapters = []
        skip_indices = set()
        
        for i, chapter in enumerate(chapters):
            if i in skip_indices:
                continue
                
            if i in small_chapters and i < len(chapters) - 1:
                # Merge with next chapter
                merged_chapter = {
                    "title": f"{chapter['title']} + {chapters[i+1]['title']}",
                    "start_index": chapter['start_index'],
                    "end_index": chapters[i+1]['end_index']
                }
                new_chapters.append(merged_chapter)
                skip_indices.add(i+1)
            else:
                new_chapters.append(chapter)
        
        chapters = new_chapters
    
    logger.info(f"Located {len(chapters)} chapters with boundaries")
    
    # Log chapter sizes
    for i, chapter in enumerate(chapters[:5]):  # Log first 5 chapters
        size = chapter['end_index'] - chapter['start_index']
        logger.info(f"Chapter {i+1}: {chapter['title']} - {size} characters")
    
    return chapters


def format_character_context(character_list):
    """Format character analysis into a context string for the transformation.
    
    Args:
        character_list: List of character dictionaries with name, gender, and role
        
    Returns:
        Formatted context string
    """
    context_parts = ["Character information:"]
    
    # Add each character to the context
    for character in character_list:
        name = character.get('name', 'Unknown')
        gender = character.get('gender', 'unknown')
        role = character.get('role', 'Unknown role')
        context_parts.append(f"- {name}: {gender}, {role}")
    
    return "\n".join(context_parts)


def transform_gender_with_context(text: str, transform_type: str, character_context: str, 
                                 model: str = "gpt-4.1-mini") -> Tuple[str, List[str]]:
    """Transform text with character context to ensure consistency.
    
    Args:
        text: The text to transform
        transform_type: Type of transformation (feminine, masculine, neutral)
        character_context: String containing character information
        model: The OpenAI model to use
        
    Returns:
        Tuple containing (transformed_text, list_of_changes)
    """
    logger = logging.getLogger()
    
    if transform_type not in TRANSFORM_TYPES:
        error_msg = f"Invalid transform type: {transform_type}. Must be one of: {', '.join(TRANSFORM_TYPES.keys())}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    client = get_openai_client()
    transform_info = TRANSFORM_TYPES[transform_type]
    
    system_prompt = f"""
    You are an expert at gender transformation in literature.
    Your task is to transform text to use {transform_info['name'].lower()} pronouns and gender references.
    Follow these rules:
    1. Change character gender references appropriately
    2. Adjust all gendered terms consistently
    3. Keep proper names but change pronouns referring to them
    4. Maintain the original writing style and flow
    5. Be thorough - don't miss any gendered references
    6. Pay special attention to possessive pronouns in relationship contexts
    7. Ensure complete consistency in pronoun usage throughout the text
    8. Double-check all instances of 'his', 'her', 'him', 'she', 'he'
    9. For neutral transformations, replace 'Mr./Mrs./Ms./Miss' with 'Mx.'
    10. Maintain consistency with the character information provided
    """
    
    user_prompt = f"""
    {transform_info['description']}.
    Make these specific changes:
    {chr(10).join(f"{i+1}. Change {change}" for i, change in enumerate(transform_info['changes']))}
    
    IMPORTANT: If this is a neutral transformation, replace all instances of Mr., Mrs., Ms., and Miss with Mx. 
    For example: "Mr. Bennet" should become "Mx. Bennet" NOT just "Bennet".
    
    Use this character information to ensure consistency:
    {character_context}
    
    Return your response as a json object in this exact format:
    {{
        "text": "<the transformed text>",
        "changes": ["Changed X to Y", ...]
    }}
    
    Text to transform:
    {text}
    """
    
    logger.info(f"Sending transformation request to {model}...")
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    
    try:
        result = json.loads(response.choices[0].message.content)
        if 'text' not in result or 'changes' not in result:
            error_msg = "API response missing required fields: 'text' and/or 'changes'"
            logger.error(error_msg)
            raise APIError(error_msg)
        
        logger.info(f"Successfully transformed text with {len(result['changes'])} changes")
        return result['text'], result['changes']
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse API response as JSON: {e}"
        logger.error(error_msg)
        raise APIError(error_msg)
    except KeyError as e:
        error_msg = f"Missing required field in API response: {e}"
        logger.error(error_msg)
        raise APIError(error_msg)


def save_debug_files(debug_dir, chapters_info, character_analysis, chunks, transformed_chunks):
    """Save intermediate files for debugging.
    
    Args:
        debug_dir: Directory to save debug files
        chapters_info: Chapter information from identify_chapters
        character_analysis: Character analysis from analyze_characters
        chunks: Original text chunks
        transformed_chunks: Transformed text chunks
    """
    logger = logging.getLogger()
    logger.info(f"Saving debug files to {debug_dir}")
    
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    # Save chapter information
    with open(os.path.join(debug_dir, "chapters_info.json"), "w") as f:
        json.dump(chapters_info, f, indent=2)
    
    # Save character analysis
    with open(os.path.join(debug_dir, "character_analysis.json"), "w") as f:
        json.dump(character_analysis, f, indent=2)
    
    # Save original chunks
    for i, chunk in enumerate(chunks):
        chunk_text = "\n\n".join(chunk)
        with open(os.path.join(debug_dir, f"chunk_{i+1}_original.txt"), "w") as f:
            f.write(chunk_text)
    
    # Save transformed chunks
    for i, chunk in enumerate(transformed_chunks):
        with open(os.path.join(debug_dir, f"chunk_{i+1}_transformed.txt"), "w") as f:
            f.write(chunk)
    
    logger.info(f"Saved {len(chunks)} original chunks and {len(transformed_chunks)} transformed chunks")


def transform_large_text(file_path: str, transform_type: str, output_path: str = None, 
                             model: str = "gpt-4.1-mini", chapters_per_chunk: int = 5,
                             debug_dir: str = "debug") -> Tuple[str, List[str]]:
    """Transform a full novel by processing it in chapter-based chunks.
    
    Args:
        file_path: Path to the text file to transform
        transform_type: Type of transformation (feminine, masculine, neutral)
        output_path: Path to save the transformed text (default: auto-generated)
        model: OpenAI model to use for transformation
        chapters_per_chunk: Number of chapters to process in each chunk
        debug_dir: Directory to save debug files
        
    Returns:
        Tuple of (transformed_text, debug_info)
    """
    # Set up logging
    logger = setup_logging()
    
    # Create debug directory if it doesn't exist
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    # Generate output path if not provided
    if output_path is None:
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        base_name = os.path.basename(file_path)
        file_name, file_ext = os.path.splitext(base_name)
        output_path = os.path.join(output_dir, f"{transform_type}_{file_name}{file_ext}")
    
    # Start the transformation process
    start_time = time.time()
    
    # Create a spinner for the transformation process
    spinner_message = "Processing..."
    spinner = cli_visuals.GenderSpinner(spinner_message, transform_type=transform_type)
    
    try:
        # Log the start of the transformation
        logger.info(f"Starting transformation of {os.path.basename(file_path)} with type: {transform_type}")
        logger.info(f"Using model: {model}, chapters per chunk: {chapters_per_chunk}")
        
        # Load the text file
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        logger.info(f"Loaded text file: {len(text)} characters")
        
        # Identify chapters using our hybrid approach
        logger.info("Identifying chapters in the text...")
        
        # Step 1: Use AI to identify chapter titles
        spinner.start()
        logger.info(f"Identifying chapter titles using {model}...")
        
        chapter_titles = identify_chapter_titles(text, model=model)
        
        # Clear spinner line before logging
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
        
        logger.info(f"Successfully identified {len(chapter_titles)} chapter titles")
        
        # Step 2: Use regex to locate chapter boundaries
        spinner.start()
        logger.info("Locating chapter boundaries in text...")
        
        boundaries = locate_chapter_boundaries(text, chapter_titles)
        
        # Clear spinner line before logging
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
        
        logger.info(f"Successfully identified {len(boundaries)} chapter boundaries")
        logger.info(f"Identified {len(boundaries)} chapters in {(time.time() - start_time):.2f} seconds")
        
        # Log a few sample chapters
        for i, (start, end) in enumerate(boundaries[:5]):
            logger.info(f"Chapter {i+1}: {start} to {end} ({end - start} characters)")
        
        # Analyze characters in the full text
        logger.info("Analyzing characters in the full text...")
        
        # Start spinner for character analysis
        spinner.start()
        character_analysis_start = time.time()
        analysis_result = analyze_characters(text, model=model)
        
        # Clear spinner line before logging
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
        
        # Extract characters from the analysis result
        characters_dict = analysis_result.get('characters', {})
        
        # Convert to a list format for easier processing
        character_list = []
        for name, char_info in characters_dict.items():
            character_list.append({
                'name': name,
                'gender': char_info.get('gender', 'unknown'),
                'role': char_info.get('role', 'Unknown role'),
                'mentions': char_info.get('mentions', []),
                'name_variants': char_info.get('name_variants', [])
            })
        
        # Log character analysis information
        logger.info(f"Identified {len(character_list)} characters in {(time.time() - character_analysis_start):.2f} seconds")
        
        # Log a few sample characters
        for i, character in enumerate(character_list[:3]):
            logger.info(f"Character: {character['name']}, Gender: {character['gender']}, Role: {character['role']}")
        
        # Process the text in chunks of chapters
        total_chunks = math.ceil(len(boundaries) / chapters_per_chunk)
        
        logger.info(f"Processing {total_chunks} chunks of approximately {chapters_per_chunk} chapters each")
        
        transformed_text = ""
        debug_info = []
        total_changes = 0
        
        # Process chapters in chunks
        for chunk_idx in range(total_chunks):
            chunk_start_time = time.time()
            start_chapter = chunk_idx * chapters_per_chunk
            end_chapter = min(start_chapter + chapters_per_chunk, len(boundaries))
            
            # Calculate progress percentage
            progress_pct = (chunk_idx / total_chunks) * 100
            
            # Get the chapters for this chunk
            chunk_chapters = boundaries[start_chapter:end_chapter]
            
            # Combine the chapters in this chunk
            chunk_text = ""
            for start, end in chunk_chapters:
                chapter_text = text[start:end]
                chunk_text += chapter_text
            
            # Calculate progress
            progress_pct = (chunk_idx / total_chunks) * 100
            
            # Log chunk information
            logger.info(f"Processing chunk {chunk_idx+1}/{total_chunks}: {len(chunk_text)} characters ({progress_pct:.1f}% complete)")
            
            # Estimate time remaining
            if chunk_idx > 0:
                elapsed_time = time.time() - start_time
                time_per_chunk = elapsed_time / chunk_idx
                remaining_chunks = total_chunks - chunk_idx
                remaining_time = time_per_chunk * remaining_chunks
                
                # Format as minutes and seconds
                remaining_minutes = int(remaining_time // 60)
                remaining_seconds = int(remaining_time % 60)
                logger.info(f"Estimated time remaining: {remaining_minutes}m {remaining_seconds:02d}s")
            
            # Transform this chunk
            logger.info(f"Sending transformation request to {model}...")
            
            # Start spinner for chunk transformation
            spinner.start()
            chunk_start_time = time.time()
            
            # Include character analysis in the transformation
            # Format character context for the transformation
            character_context = format_character_context(character_list)
            
            # Transform the chunk with character context
            try:
                chunk_result, changes = transform_gender_with_context(
                    chunk_text, 
                    transform_type, 
                    character_context,
                    model
                )
            except Exception as e:
                logger.error(f"Error transforming chunk {chunk_idx+1}: {e}")
                # Save the problematic chunk for debugging
                error_path = os.path.join(debug_dir, f"error_chunk_{chunk_idx+1}.txt")
                with open(error_path, 'w', encoding='utf-8') as f:
                    f.write(chunk_text)
                logger.info(f"Saved problematic chunk to {error_path}")
                raise
            
            # Create debug info structure
            chunk_debug = {
                "changes": changes,
                "chunk_size": len(chunk_text),
                "character_count": len(character_list)
            }
            
            # Clear spinner line before logging
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()
            
            # Log transformation results
            chunk_time = time.time() - chunk_start_time
            changes_count = len(chunk_debug.get("changes", []))
            total_changes += changes_count
            
            logger.info(f"Successfully transformed text with {changes_count} changes")
            logger.info(f"Chunk {chunk_idx+1} processed in {chunk_time:.2f} seconds with {changes_count} changes")
            
            # Log some sample changes
            changes = chunk_debug.get("changes", [])
            for i, change in enumerate(changes[:5]):
                logger.info(f"Change {i+1}: {change}")
            
            if len(changes) > 5:
                logger.info(f"... and {len(changes) - 5} more changes")
            
            # Add the transformed chunk to the result
            transformed_text += chunk_result
            debug_info.append(chunk_debug)
            
            # Log progress but don't write to file yet
            logger.info(f"Added chunk {chunk_idx+1} to memory (total: {len(transformed_text)} characters)")
            
            # Save debug information
            debug_path = os.path.join(debug_dir, f"chunk_{chunk_idx+1}_debug.json")
            with open(debug_path, 'w', encoding='utf-8') as f:
                json.dump(chunk_debug, f, indent=2)
        
        # Now write the complete transformed text to the output file
        logger.info(f"Writing complete transformed text to {output_path} ({len(transformed_text)} characters)...")
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transformed_text)
            logger.info(f"Successfully wrote transformed text to {output_path}")
        except Exception as e:
            logger.error(f"Error writing to output file: {e}")
            raise
        
        # Log completion
        total_time = time.time() - start_time
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)
        
        # Show final spinner and then clear it
        spinner.start()
        time.sleep(0.5)  # Brief pause to show the spinner
        
        # Clear spinner line and show completion checkmark
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.write(f"\r{Colors.BRIGHT_GREEN}\u2713 Processing complete{Colors.RESET}")
        sys.stdout.flush()
        print()  # Move to next line
        
        # Stop the spinner
        spinner.stop()
        
        # Log completion information
        logger.info(f"Completed in {minutes}m {seconds}s")
        logger.info(f"Made {total_changes} changes")
        logger.info(f"Transformed text saved to {output_path} ({len(transformed_text)} characters)")
        logger.info(f"Debug files saved to {debug_dir}")
        
        return transformed_text, debug_info
    
    except Exception as e:
        # Stop the spinner in case of error
        spinner.stop()
        
        # Log the error
        logger.error(f"Error during transformation: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Re-raise the exception
        raise
