#!/usr/bin/env python3
"""
Assemble the complete transformed book from individual chapter files.
"""

import json
from datetime import datetime
from pathlib import Path


def assemble_book():
    """Assemble all transformed chapters into a complete book."""
    # Load the original book for metadata
    with open('test_data/pride_and_prejudice_clean.json', 'r') as f:
        original = json.load(f)
    
    # Create output structure
    transformed_book = {
        'metadata': original['metadata'].copy(),
        'chapters': [],
        'statistics': {},
        'transformation': {
            'type': 'feminine',
            'model': 'claude-3-opus',
            'timestamp': datetime.now().isoformat(),
            'method': 'claude_direct',
            'notes': 'Gender-swapped version with all male characters becoming female and vice versa'
        }
    }
    
    # Update metadata
    transformed_book['metadata']['format_version'] = '2.0'
    transformed_book['metadata']['transformation'] = 'feminine'
    
    total_changes = 0
    total_sentences = 0
    total_words = 0
    
    # Process each chapter file
    for i in range(len(original['chapters'])):
        chapter_file = f'test_data/chapter_{i:03d}_transformed.json'
        
        if Path(chapter_file).exists():
            with open(chapter_file, 'r') as f:
                chapter_data = json.load(f)
            
            # Create chapter entry
            chapter = {
                'number': original['chapters'][i]['number'],
                'title': chapter_data['title'],
                'sentences': chapter_data['sentences'],
                'sentence_count': len(chapter_data['sentences']),
                'word_count': sum(len(s.split()) for s in chapter_data['sentences']),
                'changes': chapter_data['changes']
            }
            
            transformed_book['chapters'].append(chapter)
            total_changes += chapter_data['changes']
            total_sentences += chapter['sentence_count']
            total_words += chapter['word_count']
            
            print(f"Added {chapter['title']} - {chapter_data['changes']} changes")
        else:
            # Use original if transformed doesn't exist
            print(f"Warning: No transformed file for chapter {i}, using original")
            chapter = original['chapters'][i].copy()
            chapter['changes'] = 0
            transformed_book['chapters'].append(chapter)
            total_sentences += chapter['sentence_count']
            total_words += chapter['word_count']
    
    # Update statistics
    transformed_book['statistics'] = {
        'total_chapters': len(transformed_book['chapters']),
        'total_sentences': total_sentences,
        'total_words': total_words,
        'total_changes': total_changes,
        'transformation_rate': f"{(total_changes / total_sentences * 100):.1f}%"
    }
    
    # Save the complete book
    output_file = 'test_data/pride_and_prejudice_feminine.json'
    with open(output_file, 'w') as f:
        json.dump(transformed_book, f, indent=2, ensure_ascii=False)
    
    print(f"\nAssembled complete book:")
    print(f"  Chapters: {transformed_book['statistics']['total_chapters']}")
    print(f"  Total changes: {total_changes}")
    print(f"  Transformation rate: {transformed_book['statistics']['transformation_rate']}")
    print(f"  Saved to: {output_file}")
    
    # Also create a text version
    from book_to_json import recreate_text_from_json
    text_file = 'test_data/pride_and_prejudice_feminine.txt'
    recreate_text_from_json(output_file, text_file)
    print(f"  Text version: {text_file}")


if __name__ == '__main__':
    assemble_book()