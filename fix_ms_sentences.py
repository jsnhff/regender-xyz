#!/usr/bin/env python3
"""Fix incorrectly split sentences at 'Ms.' abbreviation."""

import json
import re

def fix_ms_splits(sentences):
    """Fix sentences incorrectly split at Ms./Mr./Mrs./Dr. etc."""
    if not sentences:
        return sentences
    
    fixed = []
    i = 0
    
    while i < len(sentences):
        current = sentences[i].strip()
        
        # Check if this sentence is just an abbreviation
        if current in ['Ms.', 'Mr.', 'Mrs.', 'Dr.', 'St.', 'Prof.']:
            # If there's a next sentence, merge them
            if i + 1 < len(sentences):
                next_sent = sentences[i + 1].strip()
                # Always merge with next sentence
                fixed.append(current + ' ' + next_sent)
                i += 2
                continue
        
        # Also check if sentence ends with abbreviation and next starts with lowercase
        if (i + 1 < len(sentences) and 
            re.search(r'\b(Ms|Mr|Mrs|Dr|St|Prof)\.$', current) and 
            sentences[i + 1].strip() and 
            sentences[i + 1].strip()[0].islower()):
            # Merge with next sentence
            fixed.append(current + ' ' + sentences[i + 1].strip())
            i += 2
            continue
        
        # Normal sentence
        fixed.append(current)
        i += 1
    
    return fixed


def fix_book_json(input_file, output_file):
    """Fix an entire book JSON file."""
    with open(input_file, 'r') as f:
        book = json.load(f)
    
    # Fix each chapter
    for chapter in book.get('chapters', []):
        if 'paragraphs' in chapter:
            for paragraph in chapter['paragraphs']:
                if 'sentences' in paragraph:
                    paragraph['sentences'] = fix_ms_splits(paragraph['sentences'])
    
    # Save fixed version
    with open(output_file, 'w') as f:
        json.dump(book, f, indent=2)
    
    print(f"Fixed book saved to: {output_file}")


if __name__ == "__main__":
    # Fix the transformed book
    fix_book_json(
        'books/json/Sorcerers_Stone_female_transformed.json',
        'books/json/Sorcerers_Stone_female_transformed_fixed.json'
    )
    
    # Recreate text from fixed JSON
    from book_parser.utils.recreate_text import recreate_text_from_json
    recreate_text_from_json(
        'books/json/Sorcerers_Stone_female_transformed_fixed.json',
        'books/output/Sorcerers_Stone_female_fixed.txt'
    )