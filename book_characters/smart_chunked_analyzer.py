"""Smart chunked character analysis that ensures complete coverage."""

import json
from typing import Dict, Any, List, Tuple, Optional
from api_client import UnifiedLLMClient
from .prompts import get_character_analysis_prompt


def analyze_book_characters_smart_chunks(
    book_data: Dict[str, Any],
    model: Optional[str] = None,
    provider: str = "grok",
    verbose: bool = True
) -> Tuple[Dict[str, Any], str]:
    """
    Analyze characters using smart chunking to ensure complete coverage.
    
    Instead of sequential chunks, we'll analyze:
    1. Beginning chapters (character introductions)
    2. Middle chapters (main plot)
    3. End chapters (resolution)
    4. Overlap zones to catch characters that appear at boundaries
    """
    if verbose:
        print("Analyzing characters with smart chunking strategy...")
    
    # Extract chapters
    chapters = book_data.get('chapters', [])
    total_chapters = len(chapters)
    
    if total_chapters == 0:
        return {}, "No chapters found"
    
    # Define smart chunks
    chunks_config = []
    
    if total_chapters <= 5:
        # Small book - analyze all at once
        chunks_config.append({
            'name': 'Complete Book',
            'chapters': list(range(total_chapters))
        })
    else:
        # Larger book - strategic chunks
        # Beginning (first 25%)
        begin_end = max(1, total_chapters // 4)
        chunks_config.append({
            'name': 'Beginning (Introduction)',
            'chapters': list(range(0, begin_end))
        })
        
        # Early-middle overlap
        early_mid_start = max(0, begin_end - 1)
        early_mid_end = min(total_chapters, begin_end + 2)
        chunks_config.append({
            'name': 'Early-Middle Transition',
            'chapters': list(range(early_mid_start, early_mid_end))
        })
        
        # Middle (40-60%)
        mid_start = int(total_chapters * 0.4)
        mid_end = int(total_chapters * 0.6)
        chunks_config.append({
            'name': 'Middle (Main Plot)',
            'chapters': list(range(mid_start, mid_end))
        })
        
        # Late-middle overlap
        late_mid_start = max(0, mid_end - 1)
        late_mid_end = min(total_chapters, mid_end + 2)
        chunks_config.append({
            'name': 'Late-Middle Transition',
            'chapters': list(range(late_mid_start, late_mid_end))
        })
        
        # End (last 25%)
        end_start = total_chapters - max(1, total_chapters // 4)
        chunks_config.append({
            'name': 'End (Resolution)',
            'chapters': list(range(end_start, total_chapters))
        })
    
    if verbose:
        print(f"  Total chapters: {total_chapters}")
        print(f"  Analysis strategy: {len(chunks_config)} strategic chunks")
        for chunk in chunks_config:
            print(f"    - {chunk['name']}: Chapters {chunk['chapters'][0]+1}-{chunk['chapters'][-1]+1}")
    
    # Initialize client
    client = UnifiedLLMClient(provider=provider)
    all_characters = {}
    
    # Process each chunk
    for i, chunk_config in enumerate(chunks_config):
        if verbose:
            print(f"\n  Analyzing {chunk_config['name']}...")
        
        # Extract text from specified chapters
        chunk_text = extract_chapters_text(chapters, chunk_config['chapters'])
        
        # Create context about chunk location
        chunk_context = f"[Analyzing {chunk_config['name']} - Chapters {chunk_config['chapters'][0]+1} to {chunk_config['chapters'][-1]+1} of {total_chapters}]"
        
        # Analyze chunk
        chunk_chars = analyze_chunk_with_context(
            chunk_text,
            model,
            client,
            chunk_context,
            chunk_num=i+1,
            total_chunks=len(chunks_config),
            verbose=verbose
        )
        
        # Merge results intelligently
        all_characters = merge_characters_smart(all_characters, chunk_chars, chunk_config['name'])
        
        if verbose:
            print(f"    Found {len(chunk_chars)} characters in this section")
            print(f"    Total unique characters so far: {len(all_characters)}")
    
    # Create character context
    from .context import create_character_context
    context = create_character_context(all_characters)
    
    if verbose:
        print(f"\n✅ Smart analysis complete! Found {len(all_characters)} unique characters")
        
        # Show character distribution
        print("\nCharacter first appearances by section:")
        section_counts = {}
        for char_name, char_info in all_characters.items():
            section = char_info.get('first_seen_in', 'Unknown')
            section_counts[section] = section_counts.get(section, 0) + 1
        
        for section, count in sorted(section_counts.items()):
            print(f"  {section}: {count} characters")
    
    return all_characters, context


def extract_chapters_text(chapters: List[Dict], chapter_indices: List[int]) -> str:
    """Extract text from specified chapters."""
    text_parts = []
    
    for idx in chapter_indices:
        if idx < len(chapters):
            chapter = chapters[idx]
            
            # Add chapter title
            if chapter.get('title'):
                text_parts.append(f"\n\nCHAPTER {idx+1}: {chapter['title']}\n")
            
            # Extract sentences
            if 'paragraphs' in chapter:
                for paragraph in chapter['paragraphs']:
                    para_text = ' '.join(paragraph.get('sentences', []))
                    text_parts.append(para_text)
            else:
                text_parts.extend(chapter.get('sentences', []))
    
    return '\n'.join(text_parts)


def analyze_chunk_with_context(
    chunk_text: str,
    model: str,
    client: UnifiedLLMClient,
    chunk_context: str,
    chunk_num: int,
    total_chunks: int,
    verbose: bool = True
) -> Dict[str, Any]:
    """Analyze a chunk with context about its location in the book."""
    
    # Custom prompt that emphasizes finding ALL characters
    system_prompt = """You are an expert literary character analyst. Your task is to identify EVERY character mentioned in the provided text section, no matter how minor."""
    
    user_prompt = f"""{chunk_context}

Analyze this text section and identify ALL characters mentioned.

CRITICAL INSTRUCTIONS:
1. Include EVERY named character, even if mentioned only once
2. Include characters who are only referenced but don't appear
3. For each character, note:
   - Full name (most complete version found)
   - Gender (from pronouns/titles: male/female/unknown)
   - Role or description
   - All name variations found
   - Whether they appear in this section or are just mentioned

IMPORTANT:
- Do not skip minor characters
- Include characters from dialogue ("Harry told me..." means Harry exists)
- Include characters from memories or references
- Each character should be listed only once with all their variations

Output as JSON:
{{
    "characters": {{
        "Character Full Name": {{
            "name": "most complete name",
            "gender": "male|female|unknown",
            "role": "description from text",
            "name_variants": ["all", "variations", "found"],
            "appears_in_section": true/false
        }}
    }}
}}

TEXT SECTION:
{chunk_text[:50000]}  

Identify ALL characters:"""
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = client.complete(
            messages=messages,
            model=model,
            temperature=0.0
        )
        
        # Parse response
        result_text = response.content.strip()
        
        # Extract JSON
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = result_text[json_start:json_end]
            data = json.loads(json_text)
            return data.get('characters', {})
        else:
            if verbose:
                print(f"    Warning: No valid JSON in response")
            return {}
            
    except Exception as e:
        if verbose:
            print(f"    Error analyzing chunk: {e}")
        return {}


def merge_characters_smart(
    existing: Dict[str, Any], 
    new: Dict[str, Any], 
    section_name: str
) -> Dict[str, Any]:
    """Intelligently merge character data, tracking where characters were first seen."""
    
    for char_name, char_info in new.items():
        # Check if this character already exists under same or similar name
        matched = False
        
        for exist_name, exist_info in list(existing.items()):
            # Check for exact match or variant match
            exist_variants = set([exist_name] + exist_info.get('name_variants', []))
            new_variants = set([char_name] + char_info.get('name_variants', []))
            
            if exist_variants & new_variants:  # Any overlap in names
                matched = True
                
                # Update existing entry
                if exist_info.get('gender') == 'unknown' and char_info.get('gender') != 'unknown':
                    exist_info['gender'] = char_info['gender']
                
                # Merge variants
                all_variants = exist_variants | new_variants
                all_variants.discard(exist_name)  # Remove the main name
                exist_info['name_variants'] = sorted(list(all_variants))
                
                # Update role if new one is more detailed
                if len(char_info.get('role', '')) > len(exist_info.get('role', '')):
                    exist_info['role'] = char_info['role']
                
                break
        
        if not matched:
            # New character - track where first seen
            char_info['first_seen_in'] = section_name
            existing[char_name] = char_info
    
    return existing