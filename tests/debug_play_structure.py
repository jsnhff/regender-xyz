#!/usr/bin/env python3
"""Debug play structure parsing."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parsers.gutenberg import GutenbergParser
from src.parsers.hierarchy import HierarchyBuilder

with open('books/texts/pg1513-Romeo_and_Juliet.txt', 'r', encoding='utf-8', errors='ignore') as f:
    raw_text = f.read()

cleaner = GutenbergParser()
cleaned_text, _ = cleaner.clean(raw_text)
lines = cleaned_text.split('\n')

# Look for Act/Scene patterns
print('ACT and SCENE markers in first 200 lines:')
for i, line in enumerate(lines[:200]):
    if 'ACT' in line.upper() or 'SCENE' in line.upper():
        print(f'{i:4}: {line[:80]}')

# Build hierarchy
builder = HierarchyBuilder()
hierarchy = builder.build_hierarchy(lines, 'play', skip_toc=True)

# Examine structure
def show_structure(section, depth=0):
    indent = '  ' * depth
    if section.type.value != 'book':
        content_info = f'{len(section.content)} lines'
        if section.subsections:
            content_info += f', {len(section.subsections)} subsections'
        print(f'{indent}{section.get_full_title()}: {content_info}')
    
    if depth < 2:  # Only go 2 levels deep
        for sub in section.subsections[:3]:  # First 3 subsections
            show_structure(sub, depth + 1)
        if len(section.subsections) > 3:
            print(f'{indent}  ... and {len(section.subsections) - 3} more')

print('\nHierarchy structure:')
show_structure(hierarchy)