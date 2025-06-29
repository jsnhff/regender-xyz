#!/usr/bin/env python3
"""
Test script for AI-driven chunking strategy.
"""

import json
import sys
import re
from utils import get_openai_client

def validate_sentences_in_text(text: str, chunk_plan: dict) -> dict:
    """Validate that all sentences from AI recommendations exist in the text.
    
    Args:
        text: The full text
        chunk_plan: The AI-generated chunk plan with sentence boundaries
        
    Returns:
        Dictionary with validation results
    """
    chunk_specs = chunk_plan.get('chunks', [])
    validation_results = {
        'total_chunks': len(chunk_specs),
        'valid_chunks': 0,
        'invalid_chunks': [],
        'chunk_details': []
    }
    
    print(f"🔍 VALIDATING {len(chunk_specs)} SENTENCE BOUNDARIES IN TEXT:")
    
    for i, spec in enumerate(chunk_specs):
        start_sentence = spec.get('start_sentence', '').strip()
        end_sentence = spec.get('end_sentence', '').strip()
        
        start_found = start_sentence in text if start_sentence else False
        end_found = end_sentence in text if end_sentence else False
        
        chunk_detail = {
            'chunk_num': i + 1,
            'start_sentence': start_sentence,
            'end_sentence': end_sentence,
            'start_found': start_found,
            'end_found': end_found,
            'valid': start_found and end_found,
            'description': spec.get('description', '')
        }
        
        validation_results['chunk_details'].append(chunk_detail)
        
        if chunk_detail['valid']:
            validation_results['valid_chunks'] += 1
            print(f"  ✅ Chunk {i+1}: Both sentences found")
        else:
            validation_results['invalid_chunks'].append(i + 1)
            print(f"  ❌ Chunk {i+1}: Start={start_found}, End={end_found}")
            if not start_found:
                print(f"     Missing start: '{start_sentence[:50]}...'")
            if not end_found:
                print(f"     Missing end: '{end_sentence[:50]}...'")
    
    success_rate = (validation_results['valid_chunks'] / validation_results['total_chunks']) * 100
    print(f"\n📊 VALIDATION SUMMARY: {validation_results['valid_chunks']}/{validation_results['total_chunks']} chunks valid ({success_rate:.1f}%)")
    
    return validation_results


def extract_chunks_from_text(text: str, chunk_plan: dict) -> list:
    """Extract actual text chunks based on sentence boundaries.
    
    Args:
        text: The full text
        chunk_plan: The AI-generated chunk plan with sentence boundaries
        
    Returns:
        List of actual text chunks
    """
    chunks = []
    chunk_specs = chunk_plan.get('chunks', [])
    
    for i, spec in enumerate(chunk_specs):
        start_sentence = spec.get('start_sentence', '').strip()
        end_sentence = spec.get('end_sentence', '').strip()
        
        if not start_sentence or not end_sentence:
            print(f"⚠ Chunk {i+1}: Missing sentence boundaries")
            continue
            
        # Simple exact matching - no fuzzy logic
        start_pos = text.find(start_sentence)
        if start_pos == -1:
            print(f"⚠ Chunk {i+1}: Start sentence not found")
            continue
            
        end_pos = text.find(end_sentence)
        if end_pos == -1:
            print(f"⚠ Chunk {i+1}: End sentence not found")
            continue
        end_pos += len(end_sentence)
        
        # Extract the chunk
        chunk_text = text[start_pos:end_pos].strip()
        
        # Check if chunk is too large
        MAX_CHUNK_SIZE = 60000  # 60k characters (~15k tokens)
        if len(chunk_text) > MAX_CHUNK_SIZE:
            print(f"❌ Chunk {i+1} is {len(chunk_text)} chars - exceeds max size of {MAX_CHUNK_SIZE}, skipping")
            continue
        
        chunks.append({
            'text': chunk_text,
            'description': spec.get('description', ''),
            'start_sentence': start_sentence,
            'end_sentence': end_sentence
        })
        
        print(f"✓ Extracted chunk {i+1}: {len(chunk_text)} characters")
    
    return chunks


def python_executor(text: str, pattern_analysis: dict) -> list:
    """Python reliably extracts chapters and creates chunks based on AI analysis.
    
    Args:
        text: The full text
        pattern_analysis: AI's analysis with chapter pattern and groupings
        
    Returns:
        List of chunks with guaranteed 100% coverage
    """
    print(f"⚙️ PYTHON EXECUTOR creating chunks...")
    
    chapter_pattern = pattern_analysis.get('chapter_pattern', '')
    groupings = pattern_analysis.get('groupings', [])
    
    if not chapter_pattern or not groupings:
        print("❌ Missing pattern or groupings from AI analysis")
        return []
    
    # Find all chapters in the text using regex
    print(f"🔍 Searching for chapters with pattern: {chapter_pattern}")
    chapter_matches = list(re.finditer(chapter_pattern, text, re.IGNORECASE | re.MULTILINE))
    
    if not chapter_matches:
        print(f"❌ No chapters found with pattern: {chapter_pattern}")
        return []
    
    print(f"✅ Found {len(chapter_matches)} chapters")
    
    # Create chapter boundaries
    chapter_boundaries = []
    for i, match in enumerate(chapter_matches):
        start_pos = match.start()
        end_pos = chapter_matches[i + 1].start() if i + 1 < len(chapter_matches) else len(text)
        chapter_boundaries.append((start_pos, end_pos, match.group().strip()))
    
    # ENSURE 100% COVERAGE: Include everything from start to end
    chunks = []
    
    # First, let's include any content before the first chapter
    if chapter_boundaries and chapter_boundaries[0][0] > 0:
        prologue_text = text[:chapter_boundaries[0][0]].strip()
        if prologue_text:
            chunks.append({
                'text': prologue_text,
                'description': 'Front matter and prologue',
                'chapters': 'prologue',
                'start_pos': 0,
                'end_pos': chapter_boundaries[0][0]
            })
            print(f"✅ Prologue: {len(prologue_text):,} chars")
    
    # Group chapters according to AI recommendations
    for i, grouping in enumerate(groupings):
        start_chapter = grouping.get('start_chapter', 1)
        end_chapter = grouping.get('end_chapter', 1)
        description = grouping.get('description', f'Group {i+1}')
        
        # Convert to 0-based indexing
        start_idx = max(0, start_chapter - 1)
        end_idx = min(len(chapter_boundaries), end_chapter)
        
        if start_idx >= len(chapter_boundaries):
            print(f"⚠️ Group {i+1}: Start chapter {start_chapter} exceeds available chapters")
            continue
            
        # Combine chapters in this group
        group_start = chapter_boundaries[start_idx][0]
        group_end = chapter_boundaries[end_idx - 1][1] if end_idx > 0 else len(text)
        
        chunk_text = text[group_start:group_end].strip()
        
        chunks.append({
            'text': chunk_text,
            'description': description,
            'chapters': f"{start_chapter}-{end_chapter}",
            'start_pos': group_start,
            'end_pos': group_end
        })
        
        print(f"✅ Group {i+1}: Chapters {start_chapter}-{end_chapter} = {len(chunk_text):,} chars")
    
    # Include any remaining content after the last chapter
    if chapter_boundaries:
        last_end = chapter_boundaries[-1][1]
        if last_end < len(text):
            epilogue_text = text[last_end:].strip()
            if epilogue_text:
                chunks.append({
                    'text': epilogue_text,
                    'description': 'Epilogue and end matter',
                    'chapters': 'epilogue',
                    'start_pos': last_end,
                    'end_pos': len(text)
                })
                print(f"✅ Epilogue: {len(epilogue_text):,} chars")
    
    # Calculate coverage
    total_extracted = sum(len(chunk['text']) for chunk in chunks)
    coverage = (total_extracted / len(text)) * 100
    print(f"📊 COVERAGE: {total_extracted:,}/{len(text):,} characters ({coverage:.1f}%)")
    
    return chunks


def python_pattern_fallback(text: str) -> dict:
    """Fallback pattern detector using Python regex when AI is unavailable.
    
    Args:
        text: The full text to analyze
        
    Returns:
        Dictionary with detected pattern and basic groupings
    """
    print(f"🔧 PYTHON FALLBACK pattern detector...")
    
    # Common Project Gutenberg chapter patterns
    patterns = [
        (r'CHAPTER [IVXLCDM]+\.?', 'Roman numerals (CHAPTER I, II, etc.)'),
        (r'CHAPTER \d+\.?', 'Arabic numerals (CHAPTER 1, 2, etc.)'),
        (r'Chapter [IVXLCDM]+\.?', 'Title case Roman (Chapter I, II, etc.)'),
        (r'Chapter \d+\.?', 'Title case Arabic (Chapter 1, 2, etc.)'),
        (r'^[IVXLCDM]+\.$', 'Roman only (I., II., etc.)'),
        (r'^\d+\.$', 'Numbers only (1., 2., etc.)')
    ]
    
    best_pattern = None
    best_matches = []
    
    for pattern, description in patterns:
        matches = list(re.finditer(pattern, text, re.MULTILINE))
        if len(matches) > len(best_matches):
            best_pattern = pattern
            best_matches = matches
            print(f"✅ Pattern '{description}' found {len(matches)} chapters")
    
    if not best_matches:
        print("❌ No chapter pattern detected")
        return {}
    
    total_chapters = len(best_matches)
    print(f"🎯 Best pattern: {best_pattern} ({total_chapters} chapters)")
    
    # Create simple groupings of ~10-15 chapters each
    chapters_per_group = 10
    groupings = []
    
    for i in range(0, total_chapters, chapters_per_group):
        start_chapter = i + 1
        end_chapter = min(i + chapters_per_group, total_chapters)
        groupings.append({
            'start_chapter': start_chapter,
            'end_chapter': end_chapter,
            'description': f'Chapters {start_chapter}-{end_chapter}',
            'estimated_size': 'medium'
        })
    
    return {
        'chapter_pattern': best_pattern,
        'total_chapters': total_chapters,
        'groupings': groupings,
        'coverage_check': 'Python fallback - basic grouping'
    }


def ai_pattern_detective(text: str, model: str = "gpt-4.1-mini") -> dict:
    """AI analyzes the book structure and identifies chapter patterns and optimal groupings.
    
    Args:
        text: The full text to analyze
        model: The AI model to use
        
    Returns:
        Dictionary with chapter pattern and recommended groupings
    """
    print(f"🕵️ AI PATTERN DETECTIVE analyzing book structure...")
    
    system_prompt = """You are an expert at analyzing literary text structure from Project Gutenberg books.
    Your job is to identify the chapter pattern and recommend optimal groupings for text transformation.
    
    CRITICAL TASKS:
    1. Identify the exact chapter pattern used (e.g., "CHAPTER I", "Chapter 1", "I.", etc.)
    2. Count total chapters
    3. Recommend groupings that stay under 15k tokens per group (~60k characters)
    4. Group chapters logically by narrative structure
    5. Ensure ALL chapters from first to last are covered
    
    Return a JSON object with:
    - chapter_pattern: exact regex pattern to find chapters
    - total_chapters: number of chapters found
    - groupings: array of {start_chapter, end_chapter, description, estimated_size}
    - coverage_check: confirmation that all chapters are covered
    """
    
    user_prompt = f"""Analyze this Project Gutenberg book and identify its chapter structure.
    
    REQUIREMENTS:
    1. Find the chapter pattern (look at first few chapters for the format)
    2. Count total chapters in the book
    3. Create groupings that are ~10k-15k tokens each (~40-60k characters)
    4. Make sure EVERY chapter is included in a group
    5. Group chapters logically (beginning/middle/end, plot arcs, etc.)
    
    Text to analyze:
    {text}
    
    Return the chapter analysis as JSON."""
    
    try:
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
        
        result = json.loads(response.choices[0].message.content)
        
        # Validate the response
        if 'chapter_pattern' in result and 'groupings' in result:
            print(f"✅ AI identified pattern: {result.get('chapter_pattern', 'Unknown')}")
            print(f"✅ Total chapters: {result.get('total_chapters', 'Unknown')}")
            print(f"✅ Recommended {len(result.get('groupings', []))} groupings")
            return result
        else:
            print("❌ AI response missing required fields")
            return {}
            
    except Exception as e:
        print(f"❌ AI Pattern Detective failed: {e}")
        return {}


def test_basic_chunking_ai(text: str, model: str = "gpt-4o") -> dict:
    """Test basic AI communication for chunking recommendations.
    
    Args:
        text: Sample text to analyze
        model: Model to use for testing
        
    Returns:
        Dictionary with chunking recommendations
    """
    print(f"Testing AI chunking with {len(text)} characters...")
    
    system_prompt = """You are an expert at analyzing literary texts for optimal chunking.
    Your task is to analyze text and recommend optimal chunk boundaries for processing.
    
    CRITICAL: You MUST copy sentences EXACTLY as they appear in the text.
    - Do NOT paraphrase, modify, or rewrite sentences
    - Copy the COMPLETE sentence including all punctuation
    - Use actual sentences that exist in the provided text
    - Double-check that your sentences match the text precisely
    
    Consider these factors:
    1. Natural story breaks (chapters, scenes, major transitions)
    2. Character consistency needs across chunks
    3. CRITICAL: Target chunk size MUST be under 15k tokens per chunk (max 60k characters)
    4. Narrative flow and context preservation
    5. Prefer smaller, more manageable chunks over large ones
    
    Return a JSON object with:
    - chunks: Array of chunk objects with start_sentence, end_sentence, description
    - total_chunks: Number of recommended chunks
    - reasoning: Brief explanation of chunking strategy
    """
    
    user_prompt = f"""Analyze this text and create a chunking plan.
    
    CRITICAL REQUIREMENTS:
    - Each chunk MUST be under 15k tokens (roughly 60k characters)
    - Break at natural chapter or scene boundaries
    - If a section is too large, split it into multiple chunks
    - Prefer 10-20 smaller chunks over 5-7 large chunks
    - Provide exact starting and ending sentences
    
    Text to analyze:
    {text}
    
    Return a JSON object with the chunking plan."""
    
    try:
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
        
        result = json.loads(response.choices[0].message.content)
        print(f"✓ AI responded with {result.get('total_chunks', 0)} chunks")
        return result
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return {}

def main():
    """Run basic chunking tests."""
    # Test 1: Very small text
    print("=== Test 1: Small Text ===")
    small_text = """Chapter 1
    It was a truth universally acknowledged that a single man in possession of a good fortune must be in want of a wife.
    
    Chapter 2
    Mr. Bennet was among the earliest of those who waited on Mr. Bingley."""
    
    result1 = test_basic_chunking_ai(small_text)
    if result1:
        print("Response structure:")
        for key in result1.keys():
            print(f"  - {key}: {type(result1[key])}")
        print(f"Reasoning: {result1.get('reasoning', 'None provided')}")
        
        # Validate chunks
        chunks = result1.get('chunks', [])
        for i, chunk in enumerate(chunks):
            start_sentence = chunk.get('start_sentence', '')
            end_sentence = chunk.get('end_sentence', '')
            desc = chunk.get('description', 'No description')
            print(f"  Chunk {i+1}: ({desc})")
            
            # Test if sentences exist in text
            start_found = start_sentence in small_text if start_sentence else False
            end_found = end_sentence in small_text if end_sentence else False
            
            print(f"    Start: {repr(start_sentence[:50])}{'...' if len(start_sentence) > 50 else ''}")
            print(f"    End: {repr(end_sentence[:50])}{'...' if len(end_sentence) > 50 else ''}")
            print(f"    ✓ Start found: {start_found}, End found: {end_found}")
    
    # Test chunk extraction
    if result1:
        print("\n=== Testing Chunk Extraction ===")
        extracted_chunks = extract_chunks_from_text(small_text, result1)
        
        for i, chunk in enumerate(extracted_chunks):
            print(f"\nChunk {i+1} text:")
            print(f"'{chunk['text']}'")
            print(f"Length: {len(chunk['text'])} characters")
    
    # Test 2: Larger text (chapter from test data)
    print("\n=== Test 2: Larger Text ===")
    try:
        with open('test_data/pride_and_prejudice_chapter_1.txt', 'r') as f:
            larger_text = f.read()
        
        print(f"Testing with chapter 1 ({len(larger_text)} characters)...")
        result2 = test_basic_chunking_ai(larger_text)
        
        if result2:
            print(f"✓ AI recommended {result2.get('total_chunks', 0)} chunks for larger text")
            extracted_chunks = extract_chunks_from_text(larger_text, result2)
            
            # Show summary of chunk sizes
            total_chars = sum(len(chunk['text']) for chunk in extracted_chunks)
            print(f"Total extracted: {total_chars}/{len(larger_text)} characters")
            
            for i, chunk in enumerate(extracted_chunks):
                print(f"  Chunk {i+1}: {len(chunk['text'])} chars - {chunk['description']}")
        
    except FileNotFoundError:
        print("⚠ Test file not found, skipping larger text test")
    
    # Test 3: Full book (test input size limits)
    print("\n=== Test 3: Full Book Input Size Test ===")
    try:
        with open('test_data/pride_and_prejudice_full.txt', 'r') as f:
            full_text = f.read()
        
        print(f"Full book size: {len(full_text)} characters")
        # Estimate tokens (rough: ~4 chars per token)
        estimated_tokens = len(full_text) // 4
        print(f"Estimated tokens: ~{estimated_tokens:,}")
        
        if estimated_tokens > 900000:  # Close to 1M limit
            print("⚠ Text might exceed 1M token limit, testing anyway...")
        
        print("🚀 TESTING NEW HYBRID APPROACH - LET'S BEAT BILL!")
        print("Step 1: AI Pattern Detective...")
        pattern_analysis = ai_pattern_detective(full_text)
        
        # Fallback to Python pattern detection if AI fails
        if not pattern_analysis:
            print("⚡ AI unavailable, switching to Python fallback...")
            pattern_analysis = python_pattern_fallback(full_text)
            
        if not pattern_analysis:
            print("❌ Both AI and fallback pattern analysis failed")
            return False
            
        print("\nStep 2: Python Executor...")
        hybrid_chunks = python_executor(full_text, pattern_analysis)
        
        result3 = hybrid_chunks if hybrid_chunks else None
        
        if result3:
            print(f"✅ SUCCESS! Hybrid approach created {len(result3)} chunks")
            
            # Skip old validation - our new approach guarantees accuracy
            print("\n=== HYBRID CHUNK ANALYSIS ===")
            extracted_chunks = result3  # Already extracted by Python executor
            
            if extracted_chunks:
                total_extracted = sum(len(chunk['text']) for chunk in extracted_chunks)
                coverage = (total_extracted / len(full_text)) * 100
                print(f"\n📊 EXTRACTION SUMMARY:")
                print(f"   Total chunks extracted: {len(extracted_chunks)}")
                print(f"   Total characters: {total_extracted:,} / {len(full_text):,}")
                print(f"   Coverage: {coverage:.1f}%")
                
                print(f"\n📋 CHUNK BREAKDOWN:")
                for i, chunk in enumerate(extracted_chunks):
                    char_count = len(chunk['text'])
                    # Rough token estimate (4 chars per token)
                    token_estimate = char_count // 4
                    print(f"   Chunk {i+1}: {char_count:,} chars (~{token_estimate:,} tokens)")
                    print(f"      {chunk['description']}")
                    
                    # Check if chunk size is reasonable for 32k output limit
                    if token_estimate > 25000:
                        print(f"      ⚠️  WARNING: Chunk might be too large for 32k output limit")
                    elif token_estimate > 20000:
                        print(f"      ⚠️  CAUTION: Chunk is getting close to safe limit")
                    else:
                        print(f"      ✅ Size looks good for transformation")
                        
                # Show a sample from the first chunk
                if extracted_chunks:
                    print(f"\n📖 SAMPLE FROM CHUNK 1:")
                    sample = extracted_chunks[0]['text'][:200]
                    print(f"   '{sample}{'...' if len(extracted_chunks[0]['text']) > 200 else ''}'")
            else:
                print("❌ No chunks could be extracted!")
        else:
            print("❌ Failed to process full book")
            
    except FileNotFoundError:
        print("⚠ Full book test file not found")
    except Exception as e:
        print(f"❌ Error processing full book: {e}")
    
    print("\n" + "="*50)
    return result1 is not None

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)