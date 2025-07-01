"""Chapter detection utilities for book transformation."""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

from api_client import UnifiedLLMClient


def identify_chapter_titles(text: str, model: str = "gpt-4o-mini", provider: Optional[str] = None) -> List[Dict[str, Any]]:
    """Identify chapter titles in the text using AI with regex validation.
    
    Uses AI to identify chapter titles and their positions, then validates with regex.
    This allows for more flexible chapter title detection while maintaining accuracy.
    
    Args:
        text: The text to process
        model: The model to use for AI analysis
        provider: The LLM provider to use
        
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
        client = UnifiedLLMClient(provider=provider)
        
        # Build kwargs based on provider capabilities
        kwargs = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "model": model,
            "temperature": 0
        }
        
        # Only add response_format for providers that support it
        if client.get_provider() in ["openai", "grok"]:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = client.complete(**kwargs)
        
        # Parse AI response
        import json
        
        # Try to parse the response
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError as e:
            # For MLX, try to extract JSON from response
            if client.get_provider() == 'mlx':
                import re
                # Look for JSON array or object
                json_match = re.search(r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]|\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response.content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse MLX JSON response: {e}")
                        return []
                else:
                    logger.warning(f"No valid JSON found in MLX response")
                    return []
            else:
                raise
        
        if not isinstance(result, list):
            # Handle case where AI returns {"chapters": [...]}
            if isinstance(result, dict) and 'chapters' in result:
                result = result['chapters']
            else:
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