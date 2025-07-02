#!/usr/bin/env python3
"""Comprehensive fix for sentence boundary issues while preserving paragraph structure."""

import json
import re
from typing import List, Dict, Any

def fix_abbreviation_splits(sentences: List[str]) -> List[str]:
    """Fix sentences incorrectly split at abbreviations like Ms., Mr., Dr., etc."""
    if not sentences:
        return sentences
    
    # Common abbreviations that shouldn't end sentences
    abbrevs = {'Ms', 'Mr', 'Mrs', 'Dr', 'St', 'Prof', 'Rev', 'Lt', 'Col', 'Sgt', 'Capt'}
    
    fixed = []
    i = 0
    
    while i < len(sentences):
        current = sentences[i].strip()
        
        # Case 1: Sentence is just "Ms." or similar
        if current in [f'{abbr}.' for abbr in abbrevs]:
            if i + 1 < len(sentences):
                # Merge with next sentence
                next_sent = sentences[i + 1].strip()
                fixed.append(f"{current} {next_sent}")
                i += 2
                continue
            else:
                # Last sentence is just abbreviation - skip it
                i += 1
                continue
        
        # Case 2: Sentence ends with abbreviation followed by quote and period
        # e.g., 'But I can promise a wet night tonight." Ms.'
        if re.search(r'"\s*(' + '|'.join(abbrevs) + r')\.$', current):
            if i + 1 < len(sentences):
                next_sent = sentences[i + 1].strip()
                # Remove the trailing abbreviation and merge with next
                current = re.sub(r'"\s*(' + '|'.join(abbrevs) + r')\.$', '"', current)
                abbrev = re.search(r'"\s*(' + '|'.join(abbrevs) + r')\.$', sentences[i]).group(1)
                fixed.append(current)
                # Add the abbreviation to the beginning of next sentence
                if next_sent:
                    fixed.append(f"{abbrev}. {next_sent}")
                    i += 2
                    continue
            else:
                # Just remove the trailing abbreviation
                current = re.sub(r'"\s*(' + '|'.join(abbrevs) + r')\.$', '"', current)
                fixed.append(current)
                i += 1
                continue
        
        # Case 3: Sentence ends with abbreviation and was incorrectly split
        abbrev_match = re.search(r'\b(' + '|'.join(abbrevs) + r')\.$', current)
        if abbrev_match and i + 1 < len(sentences):
            next_sent = sentences[i + 1].strip()
            # Always merge if next sentence exists
            fixed.append(f"{current} {next_sent}")
            i += 2
            continue
        
        # Case 4: Check if current sentence is a fragment that should be merged
        # e.g., "and Ms." or "Potter was Ms."
        if (current.endswith('.') and 
            re.search(r'\b(' + '|'.join(abbrevs) + r')\.$', current) and
            len(current.split()) <= 5):  # Short fragment
            if i + 1 < len(sentences):
                next_sent = sentences[i + 1].strip()
                fixed.append(f"{current} {next_sent}")
                i += 2
                continue
        
        # Case 5: Fix double periods (..)
        current = re.sub(r'\.\.+', '.', current)
        
        # Normal sentence
        fixed.append(current)
        i += 1
    
    return fixed


def fix_book_comprehensive(original_json: str, transformed_json: str, output_json: str):
    """
    Fix the transformed book using the original as reference for structure.
    
    Args:
        original_json: Path to original book JSON (for paragraph structure)
        transformed_json: Path to transformed book JSON (with broken sentences)
        output_json: Path to save fixed book
    """
    # Load both books
    with open(original_json, 'r') as f:
        original = json.load(f)
    
    with open(transformed_json, 'r') as f:
        transformed = json.load(f)
    
    # Create fixed book starting with transformed data
    fixed_book = transformed.copy()
    
    # Process each chapter
    for ch_idx, (orig_ch, trans_ch) in enumerate(zip(original['chapters'], transformed['chapters'])):
        print(f"Processing Chapter {ch_idx + 1}...")
        
        # First, collect ALL sentences from transformed chapter into one list
        all_trans_sentences = []
        para_boundaries = []  # Track where each paragraph starts
        
        for para in trans_ch.get('paragraphs', []):
            para_boundaries.append(len(all_trans_sentences))
            all_trans_sentences.extend(para.get('sentences', []))
        
        # Fix all sentences as one continuous list
        all_fixed_sentences = fix_abbreviation_splits(all_trans_sentences)
        
        # Now we need to map fixed sentences back to original paragraph structure
        # The challenge: the number of sentences has changed due to merging
        
        # Get original paragraph sentence counts
        orig_para_sent_counts = []
        for para in orig_ch.get('paragraphs', []):
            orig_para_sent_counts.append(len(para.get('sentences', [])))
        
        # Reconstruct paragraphs trying to match original counts
        fixed_paragraphs = []
        sent_idx = 0
        
        for para_idx, target_count in enumerate(orig_para_sent_counts):
            para_sentences = []
            
            # Special handling for title paragraphs (usually 1 sentence)
            if para_idx == 0 and target_count == 1:
                # Check if first sentence looks like a title
                if sent_idx < len(all_fixed_sentences):
                    first_sent = all_fixed_sentences[sent_idx]
                    # If it contains "THE GIRL WHO LIVED" or similar, extract just the title
                    if "THE GIRL WHO LIVED" in first_sent:
                        # Extract just the title part
                        if " Ms." in first_sent:
                            title_part = first_sent.split(" Ms.")[0]
                            # The rest should be part of next paragraph
                            remainder = "Ms." + first_sent.split(" Ms.", 1)[1]
                            para_sentences.append(title_part)
                            # Insert remainder at beginning of sentence list
                            all_fixed_sentences.insert(sent_idx + 1, remainder)
                        else:
                            para_sentences.append(first_sent)
                        sent_idx += 1
                    else:
                        para_sentences.append(first_sent)
                        sent_idx += 1
            else:
                # Regular paragraph - try to match original sentence count
                # This is approximate since sentence merging changes counts
                for _ in range(target_count):
                    if sent_idx < len(all_fixed_sentences):
                        para_sentences.append(all_fixed_sentences[sent_idx])
                        sent_idx += 1
            
            if para_sentences:
                fixed_paragraphs.append({'sentences': para_sentences})
        
        # Handle any remaining sentences
        if sent_idx < len(all_fixed_sentences):
            # Add remaining sentences to last paragraph
            if fixed_paragraphs:
                fixed_paragraphs[-1]['sentences'].extend(all_fixed_sentences[sent_idx:])
            else:
                fixed_paragraphs.append({'sentences': all_fixed_sentences[sent_idx:]})
        
        # Update chapter with fixed paragraphs
        fixed_book['chapters'][ch_idx]['paragraphs'] = fixed_paragraphs
        
        # Verify paragraph count matches
        orig_para_count = len(orig_ch.get('paragraphs', []))
        fixed_para_count = len(fixed_paragraphs)
        if orig_para_count != fixed_para_count:
            print(f"  Warning: Chapter {ch_idx + 1} paragraph count mismatch: "
                  f"original={orig_para_count}, fixed={fixed_para_count}")
    
    # Save fixed book
    with open(output_json, 'w') as f:
        json.dump(fixed_book, f, indent=2)
    
    print(f"\nFixed book saved to: {output_json}")
    
    # Show some statistics
    total_orig_paras = sum(len(ch.get('paragraphs', [])) for ch in original['chapters'])
    total_fixed_paras = sum(len(ch.get('paragraphs', [])) for ch in fixed_book['chapters'])
    print(f"Total paragraphs - Original: {total_orig_paras}, Fixed: {total_fixed_paras}")


def verify_fix(fixed_json: str):
    """Verify the fix by checking for common issues."""
    with open(fixed_json, 'r') as f:
        book = json.load(f)
    
    issues = []
    
    for ch_idx, chapter in enumerate(book['chapters']):
        for para_idx, para in enumerate(chapter.get('paragraphs', [])):
            for sent_idx, sent in enumerate(para.get('sentences', [])):
                # Check for standalone abbreviations
                if sent.strip() in ['Ms.', 'Mr.', 'Mrs.', 'Dr.']:
                    issues.append(f"Chapter {ch_idx+1}, Para {para_idx+1}, Sent {sent_idx+1}: "
                                f"Standalone abbreviation: '{sent}'")
                
                # Check for fragments starting with "and Ms." etc
                if re.match(r'^(and|or|but)\s+(Ms|Mr|Mrs|Dr)\.', sent.strip()):
                    issues.append(f"Chapter {ch_idx+1}, Para {para_idx+1}, Sent {sent_idx+1}: "
                                f"Fragment: '{sent[:50]}...'")
    
    if issues:
        print(f"\nFound {len(issues)} potential issues:")
        for issue in issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
    else:
        print("\nNo obvious sentence boundary issues found!")


if __name__ == "__main__":
    print("Applying comprehensive fix to maintain original paragraph structure...")
    
    # Apply the fix
    fix_book_comprehensive(
        'books/json/Sorcerers_Stone_clean.json',
        'books/json/Sorcerers_Stone_female_transformed.json',
        'books/json/Sorcerers_Stone_female_comprehensive_fixed.json'
    )
    
    # Verify the fix
    print("\nVerifying fix...")
    verify_fix('books/json/Sorcerers_Stone_female_comprehensive_fixed.json')
    
    # Recreate text from fixed JSON
    print("\nRecreating text file...")
    from book_parser.utils.recreate_text import recreate_text_from_json
    recreate_text_from_json(
        'books/json/Sorcerers_Stone_female_comprehensive_fixed.json',
        'books/output/Sorcerers_Stone_female_comprehensive_fixed.txt'
    )