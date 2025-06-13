#!/usr/bin/env python
from large_text_transform import identify_chapter_titles
import logging

logging.basicConfig(level=logging.INFO)
text = open('pride_and_prejudice_chapters_1-to-5.txt').read()
chapters = identify_chapter_titles(text)
print('\nFound chapters:')
for i, chapter in enumerate(chapters):
    print(f"{i+1}. {chapter['title']} at pos {chapter['position']} ({chapter['length']} chars)") 