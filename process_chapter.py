#!/usr/bin/env python3
"""
Process a single chapter for gender transformation.
"""

import json
import sys


def transform_sentence_feminine(sentence: str) -> str:
    """Transform a single sentence to feminine representation."""
    # Basic word replacements
    replacements = {
        # Titles
        'Mr.': 'Ms.',
        'Sir ': 'Madam ',
        'sir ': 'madam ',
        'sir,': 'madam,',
        'sir.': 'madam.',
        'sir!': 'madam!',
        'sir?': 'madam?',
        
        # Pronouns (careful with context)
        ' he ': ' she ',
        ' He ': ' She ',
        'He ': 'She ',
        ' him ': ' her ',
        ' him,': ' her,',
        ' him.': ' her.',
        ' him!': ' her!',
        ' him?': ' her?',
        ' his ': ' her ',
        ' His ': ' Her ',
        'His ': 'Her ',
        ' himself': ' herself',
        
        # Gendered nouns
        'gentleman': 'lady',
        'Gentleman': 'Lady',
        'gentlemen': 'ladies',
        'Gentlemen': 'Ladies',
        ' man ': ' woman ',
        ' Man ': ' Woman ',
        ' men ': ' women ',
        ' Men ': ' Women ',
        'young man': 'young woman',
        'Young man': 'Young woman',
        'young men': 'young women',
        
        # Family terms
        'father': 'mother',
        'Father': 'Mother',
        'brother': 'sister',
        'Brother': 'Sister',
        'son': 'daughter',
        'Son': 'Daughter',
        'husband': 'wife',
        'Husband': 'Wife',
        'nephew': 'niece',
        'Nephew': 'Niece',
        'uncle': 'aunt',
        'Uncle': 'Aunt',
        
        # Other terms
        'master': 'mistress',
        'Master': 'Mistress',
        'lord': 'lady',
        'Lord': 'Lady',
    }
    
    result = sentence
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    return result


def process_chapter(chapter_num: int):
    """Process a specific chapter number."""
    # Load the book
    with open('test_data/pride_and_prejudice_clean.json', 'r') as f:
        book = json.load(f)
    
    if chapter_num >= len(book['chapters']):
        print(f"Chapter {chapter_num} not found")
        return
    
    chapter = book['chapters'][chapter_num]
    print(f"Processing {chapter['title']} - {len(chapter['sentences'])} sentences")
    
    # Transform each sentence
    transformed = []
    changes = 0
    
    for i, sentence in enumerate(chapter['sentences']):
        new_sentence = transform_sentence_feminine(sentence)
        if new_sentence != sentence:
            changes += 1
            print(f"  Change {changes}: sentence {i}")
        transformed.append(new_sentence)
    
    # Save to output file
    output = {
        'chapter_num': chapter_num,
        'title': chapter['title'],
        'sentences': transformed,
        'changes': changes
    }
    
    with open(f'test_data/chapter_{chapter_num:03d}_transformed.json', 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Saved chapter {chapter_num} with {changes} changes")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        chapter_num = int(sys.argv[1])
    else:
        chapter_num = 0
    
    process_chapter(chapter_num)