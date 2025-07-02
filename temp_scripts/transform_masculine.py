#!/usr/bin/env python3
"""Transform Pride and Prejudice to masculine version."""

import json
import sys
from book_transform.transform import transform_book

def main():
    # Load the test book
    with open('books/json/pg1342-Pride_and_Prejudice_test.json', 'r') as f:
        book_data = json.load(f)
    
    # Load the character analysis
    with open('books/json/pg1342-Pride_and_Prejudice_test_characters.json', 'r') as f:
        character_data = json.load(f)
    
    # Add character context to book data
    book_data['character_context'] = character_data.get('context', '')
    
    print("Transforming Pride and Prejudice (first 3 chapters) to masculine version...")
    
    # Transform with masculine type
    transformed = transform_book(
        book_data=book_data,
        transform_type='masculine',  # Use masculine directly
        model='grok-3-latest',
        provider='grok',
        verbose=True
    )
    
    # Save JSON output
    with open('books/json/pg1342-Pride_and_Prejudice_test_masculine.json', 'w') as f:
        json.dump(transformed, f, indent=2)
    
    # Convert to text format
    print("\n📝 Converting to text format...")
    text_lines = []
    
    # Add title and author
    if 'metadata' in transformed:
        text_lines.append(transformed['metadata'].get('title', 'Unknown Title'))
        text_lines.append('')
        text_lines.append(f"by {transformed['metadata'].get('author', 'Unknown Author')}")
        text_lines.append('')
    
    # Add chapters
    for chapter in transformed.get('chapters', []):
        # Add chapter content
        if 'paragraphs' in chapter:
            for paragraph in chapter['paragraphs']:
                para_text = ' '.join(paragraph.get('sentences', []))
                if para_text:
                    text_lines.append(para_text)
                    text_lines.append('')
        elif 'sentences' in chapter:
            # Old format compatibility
            for sentence in chapter['sentences']:
                text_lines.append(sentence)
            text_lines.append('')
    
    # Save text output
    with open('books/output/pg1342-Pride_and_Prejudice_test_masculine.txt', 'w') as f:
        f.write('\n'.join(text_lines))
    
    print("✅ Transformation complete!")
    print(f"✓ JSON saved to: books/json/pg1342-Pride_and_Prejudice_test_masculine.json")
    print(f"✓ Text saved to: books/output/pg1342-Pride_and_Prejudice_test_masculine.txt")

if __name__ == "__main__":
    main()