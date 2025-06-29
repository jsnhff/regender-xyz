#!/usr/bin/env python3
"""
BULLETPROOF CHUNKING SOLUTION
Hybrid AI + Python approach to achieve 100% coverage for any Project Gutenberg book.
"""

import json
import re
from utils import get_openai_client

def ai_chapter_analyzer(text: str, model: str = "gpt-4.1-mini") -> dict:
    """AI analyzes the book structure and identifies the exact chapter pattern.
    
    Args:
        text: The full text to analyze
        model: The AI model to use
        
    Returns:
        Dictionary with chapter pattern and recommended chunk sizes
    """
    print("🕵️ AI CHAPTER ANALYZER: Finding the perfect chapter pattern...")
    
    system_prompt = """You are an expert at analyzing Project Gutenberg book structures.
    Your job is to identify the EXACT chapter pattern used in this book.
    
    CRITICAL REQUIREMENTS:
    1. Identify the precise regex pattern to find ALL chapters
    2. Count the total number of chapters
    3. Recommend how many chapters to group together (target ~15k tokens per chunk)
    
    Return JSON with:
    - chapter_regex: exact regex pattern to match chapters
    - total_chapters: total count of chapters found
    - chapters_per_chunk: recommended chapters per chunk for ~15k tokens
    - sample_chapters: first 3 chapter titles found
    """
    
    user_prompt = f"""Analyze this Project Gutenberg book and find its chapter pattern.
    
    Look for patterns like:
    - "CHAPTER I", "CHAPTER II" (Roman numerals)
    - "Chapter 1", "Chapter 2" (Arabic numbers)
    - "CHAPTER ONE", "CHAPTER TWO" (spelled out)
    
    Find the EXACT pattern and count ALL chapters in the book.
    
    Text to analyze:
    {text}
    
    Return the analysis as JSON."""
    
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
        
        if 'chapter_regex' in result and 'total_chapters' in result:
            print(f"✅ AI found pattern: {result['chapter_regex']}")
            print(f"✅ Total chapters: {result['total_chapters']}")
            print(f"✅ Recommended chapters per chunk: {result.get('chapters_per_chunk', 'unknown')}")
            return result
        else:
            print("❌ AI response missing required fields")
            return {}
            
    except Exception as e:
        print(f"❌ AI analyzer failed: {e}")
        return {}

def python_pattern_detector(text: str) -> dict:
    """Python fallback to detect chapter patterns when AI is unavailable."""
    print("🔧 PYTHON PATTERN DETECTOR: Scanning for chapter patterns...")
    
    # Test common patterns and find the best match
    patterns = [
        (r'CHAPTER [LXIVCDM]+\.?\s*$', 'CHAPTER + Roman (CHAPTER I, II, III...)'),
        (r'CHAPTER \d+\.?\s*$', 'CHAPTER + Number (CHAPTER 1, 2, 3...)'),
        (r'Chapter [LXIVCDM]+\.?\s*$', 'Chapter + Roman (Chapter I, II, III...)'),
        (r'Chapter \d+\.?\s*$', 'Chapter + Number (Chapter 1, 2, 3...)'),
        (r'^[LXIVCDM]+\.\s*$', 'Roman only (I., II., III....)'),
        (r'^\d+\.\s*$', 'Number only (1., 2., 3....)'),
    ]
    
    best_pattern = None
    best_count = 0
    best_description = ""
    
    for pattern, description in patterns:
        matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
        count = len(matches)
        
        if count > best_count:
            best_pattern = pattern
            best_count = count
            best_description = description
            
        print(f"  Pattern '{description}': {count} matches")
    
    if best_count == 0:
        print("❌ No chapter pattern found!")
        return {}
    
    print(f"🎯 Best pattern: {best_description} ({best_count} chapters)")
    
    # Estimate chapters per chunk (target ~15k tokens = ~60k chars)
    # Estimate: total_text / total_chapters = avg_chapter_size
    avg_chapter_size = len(text) // best_count if best_count > 0 else 10000
    chapters_per_chunk = max(1, 60000 // avg_chapter_size)
    
    return {
        'chapter_regex': best_pattern,
        'total_chapters': best_count,
        'chapters_per_chunk': chapters_per_chunk,
        'sample_chapters': ['Detected with Python fallback']
    }

def bulletproof_chunker(text: str, analysis: dict) -> list:
    """Creates chunks with guaranteed 100% text coverage."""
    print("⚙️ BULLETPROOF CHUNKER: Creating 100% coverage chunks...")
    
    chapter_regex = analysis.get('chapter_regex', '')
    chapters_per_chunk = analysis.get('chapters_per_chunk', 10)
    total_chapters = analysis.get('total_chapters', 0)
    
    if not chapter_regex:
        print("❌ No chapter pattern provided")
        return []
    
    # Find ALL chapter positions
    chapter_matches = list(re.finditer(chapter_regex, text, re.MULTILINE | re.IGNORECASE))
    actual_chapters = len(chapter_matches)
    
    print(f"🔍 Found {actual_chapters} chapters (expected {total_chapters})")
    
    if actual_chapters == 0:
        print("❌ No chapters found with the pattern!")
        return []
    
    chunks = []
    
    # STEP 1: Include everything BEFORE first chapter (prologue/front matter)
    first_chapter_pos = chapter_matches[0].start()
    if first_chapter_pos > 0:
        prologue = text[:first_chapter_pos]  # Don't strip!
        if prologue:
            chunks.append({
                'text': prologue,
                'description': 'Front matter and prologue',
                'chapters': 'prologue',
                'size': len(prologue),
                'start_pos': 0,
                'end_pos': first_chapter_pos
            })
            print(f"✅ Prologue: {len(prologue):,} characters")
    
    # STEP 2: Group chapters into chunks  
    for i in range(0, actual_chapters, chapters_per_chunk):
        start_chapter_idx = i
        end_chapter_idx = min(i + chapters_per_chunk - 1, actual_chapters - 1)
        
        # Get text from start of first chapter to start of next group (or end of text)
        chunk_start = chapter_matches[start_chapter_idx].start()
        
        if i + chapters_per_chunk < actual_chapters:
            # Not the last chunk - go to start of next chapter group
            chunk_end = chapter_matches[i + chapters_per_chunk].start()
        else:
            # Last chunk - go to absolute end of text to ensure 100% coverage
            chunk_end = len(text)
        
        chunk_text = text[chunk_start:chunk_end]  # Don't strip!
        
        start_chapter_num = start_chapter_idx + 1
        end_chapter_num = end_chapter_idx + 1
        
        chunks.append({
            'text': chunk_text,
            'description': f'Chapters {start_chapter_num}-{end_chapter_num}',
            'chapters': f'{start_chapter_num}-{end_chapter_num}',
            'size': len(chunk_text),
            'start_pos': chunk_start,
            'end_pos': chunk_end
        })
        
        print(f"✅ Chunk {len(chunks)}: Chapters {start_chapter_num}-{end_chapter_num} = {len(chunk_text):,} chars")
    
    # VERIFY 100% COVERAGE
    total_chunk_size = sum(chunk['size'] for chunk in chunks)
    coverage = (total_chunk_size / len(text)) * 100
    
    print(f"\n📊 COVERAGE VERIFICATION:")
    print(f"   Original text: {len(text):,} characters")
    print(f"   Chunked text: {total_chunk_size:,} characters")
    print(f"   Coverage: {coverage:.1f}%")
    
    if coverage >= 99.995:
        print("✅ 100% COVERAGE ACHIEVED!")
    else:
        print("❌ Coverage gap detected!")
        gap = len(text) - total_chunk_size
        print(f"   Missing: {gap:,} characters")
        
        # DEBUG: Let's find what's missing!
        print(f"\n🔍 DEBUGGING THE {gap} MISSING CHARACTERS:")
        covered_ranges = []
        for chunk in chunks:
            start = chunk.get('start_pos', 0)
            end = chunk.get('end_pos', start + chunk['size'])
            covered_ranges.append((start, end))
        
        # Sort ranges and find gaps
        covered_ranges.sort()
        print(f"   Covered ranges: {len(covered_ranges)}")
        
        for i in range(len(covered_ranges) - 1):
            current_end = covered_ranges[i][1]
            next_start = covered_ranges[i + 1][0]
            
            if next_start > current_end:
                gap_size = next_start - current_end
                gap_text = text[current_end:next_start]
                print(f"   Gap {i+1}: positions {current_end}-{next_start} ({gap_size} chars)")
                print(f"   Content: {repr(gap_text[:100])}")
        
        # Check if there's missing text at the very end
        if covered_ranges:
            last_end = covered_ranges[-1][1]
            if last_end < len(text):
                final_gap = len(text) - last_end
                final_text = text[last_end:]
                print(f"   Final gap: positions {last_end}-{len(text)} ({final_gap} chars)")
                print(f"   Content: {repr(final_text[:100])}")
    
    return chunks

def test_bulletproof_approach():
    """Test the bulletproof chunking approach."""
    print("🚀 TESTING BULLETPROOF CHUNKING APPROACH!")
    print("=" * 60)
    
    # Load the full book
    try:
        with open('test_data/pride_and_prejudice_full.txt', 'r') as f:
            full_text = f.read()
    except FileNotFoundError:
        print("❌ Test file not found!")
        return False
    
    print(f"📚 Loaded book: {len(full_text):,} characters")
    
    # Step 1: Try AI analysis first
    print("\n" + "="*60)
    analysis = ai_chapter_analyzer(full_text)
    
    # Step 2: Fallback to Python if AI fails
    if not analysis:
        print("\n⚡ AI unavailable, using Python fallback...")
        analysis = python_pattern_detector(full_text)
    
    if not analysis:
        print("❌ Both AI and Python analysis failed!")
        return False
    
    # Step 3: Create bulletproof chunks
    print("\n" + "="*60)
    chunks = bulletproof_chunker(full_text, analysis)
    
    if not chunks:
        print("❌ Chunking failed!")
        return False
    
    # Step 4: Analyze results
    print("\n" + "="*60)
    print("📋 FINAL CHUNK ANALYSIS:")
    
    for i, chunk in enumerate(chunks, 1):
        size_tokens = chunk['size'] // 4  # Rough estimate
        status = "✅ Perfect size"
        
        if size_tokens > 25000:
            status = "⚠️ Too large for 32k output"
        elif size_tokens > 20000:
            status = "⚠️ Close to limit"
        
        print(f"   Chunk {i}: {chunk['size']:,} chars (~{size_tokens:,} tokens) - {chunk['description']} - {status}")
    
    print(f"\n🎯 FINAL RESULT:")
    print(f"   Total chunks: {len(chunks)}")
    total_size = sum(chunk['size'] for chunk in chunks)
    coverage = (total_size / len(full_text)) * 100
    print(f"   Coverage: {coverage:.1f}%")
    
    success = coverage >= 99.9
    print(f"   Status: {'🏆 SUCCESS - BILL IS BEATEN!' if success else '❌ NEEDS MORE WORK'}")
    
    return success

if __name__ == "__main__":
    success = test_bulletproof_approach()
    exit(0 if success else 1)