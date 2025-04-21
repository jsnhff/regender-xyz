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
from typing import Dict, List, Tuple, Any
from datetime import datetime

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
        logging.INFO: WHITE + "✓ %(message)s" + RESET + BRIGHT_BLACK + " [%(asctime)s]" + RESET,
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


def identify_chapters(text: str, model: str = "gpt-4.1-mini") -> List[Dict]:
    """Use the AI to identify chapters in a text.
    
    Args:
        text: The full text to analyze
        model: The OpenAI model to use
        
    Returns:
        List of dictionaries with chapter info: 
        [{"title": "Chapter I", "start_index": 309, "end_index": 1200}, ...]
    """
    logger = logging.getLogger()
    logger.info("Identifying chapters using AI...")
    
    client = get_openai_client()
    
    system_prompt = """
    You are an expert at analyzing literary text structure.
    Your task is to identify the chapters in this book and their boundaries.
    Ignore illustrations, front matter, and other non-chapter content.
    """
    
    user_prompt = f"""
    Analyze this text and identify all chapters.
    For each chapter, provide:
    1. The chapter title (e.g., "Chapter I", "Chapter II", etc.)
    2. The approximate start position (character index)
    3. The approximate end position (character index)
    
    Return your response as a JSON object with this structure:
    {{
      "chapters": [
        {{"title": "Chapter I", "start_index": X, "end_index": Y}},
        {{"title": "Chapter II", "start_index": Y+1, "end_index": Z}},
        ...
      ]
    }}
    
    Text to analyze:
    {text}
    """
    
    logger.info(f"Sending chapter identification request to {model}...")
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
        chapters = result.get("chapters", [])
        
        # Validate chapter structure
        for chapter in chapters:
            if not all(key in chapter for key in ["title", "start_index", "end_index"]):
                raise ValueError(f"Invalid chapter structure: {chapter}")
        
        logger.info(f"Successfully identified {len(chapters)} chapters")
        return chapters
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        error_msg = f"Failed to parse chapter identification response: {e}"
        logger.error(error_msg)
        raise APIError(error_msg)


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
    spinner_message = f"Transforming novel to {transform_type}"
    spinner = cli_visuals.GenderSpinner(spinner_message, transform_type=transform_type)
    
    try:
        # Log the start of the transformation
        logger.info(f"Starting transformation of {os.path.basename(file_path)} with type: {transform_type}")
        logger.info(f"Using model: {model}, chapters per chunk: {chapters_per_chunk}")
        
        # Load the text file
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        logger.info(f"Loaded text file: {len(text)} characters")
        
        # Identify chapters in the text
        logger.info("Identifying chapters in the text...")
        logger.info("Identifying chapters using AI...")
        
        # Start spinner for chapter identification
        spinner.start()
        logger.info(f"Sending chapter identification request to {model}...")
        
        chapters = identify_chapters(text, model=model)
        
        # Log chapter information
        # Clear spinner line before logging
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
        
        logger.info(f"Successfully identified {len(chapters)} chapters")
        logger.info(f"Identified {len(chapters)} chapters in {(time.time() - start_time):.2f} seconds")
        
        # Log a few sample chapters
        for i, chapter in enumerate(chapters[:3]):
            logger.info(f"Chapter {i+1}: {chapter['title']} - {chapter['end_index'] - chapter['start_index']} chars")
        
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
        total_chunks = math.ceil(len(chapters) / chapters_per_chunk)
        
        logger.info(f"Processing {total_chunks} chunks of approximately {chapters_per_chunk} chapters each")
        
        transformed_text = ""
        debug_info = []
        total_changes = 0
        
        # Process each chunk
        for chunk_idx in range(total_chunks):
            chunk_start = chunk_idx * chapters_per_chunk
            chunk_end = min(chunk_start + chapters_per_chunk, len(chapters))
            chunk_chapters = chapters[chunk_start:chunk_end]
            
            # Combine the chapters in this chunk
            chunk_text = ""
            for chapter in chunk_chapters:
                chapter_text = text[chapter['start_index']:chapter['end_index']]
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
            chunk_result, changes = transform_gender_with_context(
                chunk_text, 
                transform_type, 
                character_context,
                model
            )
            
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
            
            # Save intermediate results
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transformed_text)
            
            # Save debug information
            debug_path = os.path.join(debug_dir, f"chunk_{chunk_idx+1}_debug.json")
            with open(debug_path, 'w', encoding='utf-8') as f:
                json.dump(chunk_debug, f, indent=2)
        
        # Log completion
        total_time = time.time() - start_time
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)
        
        # Show final spinner and then clear it
        spinner.start()
        time.sleep(0.5)  # Brief pause to show the spinner
        
        # Clear spinner line and show completion checkmark
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.write(f"\r{Colors.BRIGHT_GREEN}\u2713 {spinner_message}{Colors.RESET}")
        sys.stdout.flush()
        print()  # Move to next line
        
        # Stop the spinner
        spinner.stop()
        
        # Log completion information
        logger.info(f"Completed in {minutes}m {seconds}s")
        logger.info(f"Made {total_changes} changes")
        logger.info(f"Transformed text saved to {output_path}")
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
