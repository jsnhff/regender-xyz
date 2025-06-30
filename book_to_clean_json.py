#!/usr/bin/env python3
"""
Integrated book parser that converts Gutenberg texts to clean JSON format.

This combines the refined parser with sentence splitting and cleaning
to produce JSON files ready for gender transformation.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from book_parser_v2 import BookParserV2, parse_book, Section, SectionType


class SentenceSplitter:
    """Enhanced sentence splitter for books."""
    
    # Common abbreviations
    ABBREVIATIONS = [
        'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.', 'Sr.', 'Jr.', 'Ph.D.', 'M.D.',
        'B.A.', 'M.A.', 'D.D.S.', 'Inc.', 'Ltd.', 'Co.', 'Corp.',
        'vs.', 'etc.', 'i.e.', 'e.g.', 'cf.', 'al.', 'No.', 'Vol.',
        'Jan.', 'Feb.', 'Mar.', 'Apr.', 'Jun.', 'Jul.', 'Aug.', 'Sep.',
        'Sept.', 'Oct.', 'Nov.', 'Dec.', 'Mon.', 'Tue.', 'Wed.', 'Thu.',
        'Fri.', 'Sat.', 'Sun.', 'St.', 'Ave.', 'Rd.', 'Blvd.',
        # Add from books
        'Hon.', 'Rev.', 'Capt.', 'Col.', 'Gen.', 'Lt.', 'Maj.', 'Sgt.',
        'Esq.', 'M.P.', 'U.S.', 'U.K.', 'A.M.', 'P.M.',
    ]
    
    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences with improved handling."""
        if not text:
            return []
        
        # Protect abbreviations
        protected_text = text
        for abbr in self.ABBREVIATIONS:
            protected_text = protected_text.replace(abbr, abbr.replace('.', '<!DOT!>'))
        
        # Protect ellipsis
        protected_text = protected_text.replace('...', '<!ELLIPSIS!>')
        
        # Split on sentence endings
        # Handle various quotation styles
        patterns = [
            # Standard sentence ending
            r'([.!?])\s+(?=[A-Z])',
            # With closing quotes
            r'([.!?]["\'])\s+(?=[A-Z])',
            r'([.!?]")\s+(?=[A-Z])',
            r"([.!?]')\s+(?=[A-Z])",
        ]
        
        # Apply patterns
        for pattern in patterns:
            protected_text = re.sub(pattern, r'\1<|SPLIT|>', protected_text)
        
        # Split on markers
        sentences = protected_text.split('<|SPLIT|>')
        
        # Clean and restore
        cleaned_sentences = []
        for sentence in sentences:
            # Restore protected elements
            sentence = sentence.replace('<!DOT!>', '.')
            sentence = sentence.replace('<!ELLIPSIS!>', '...')
            
            # Clean whitespace
            sentence = sentence.strip()
            
            # Skip empty or very short
            if len(sentence) < 2:
                continue
            
            cleaned_sentences.append(sentence)
        
        return cleaned_sentences


class BookToCleanJSON:
    """Convert books to clean JSON format for transformation."""
    
    def __init__(self):
        self.parser = BookParserV2(strict_mode=True)
        self.splitter = SentenceSplitter()
    
    def process_book(self, filepath: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a book file to clean JSON format.
        
        Args:
            filepath: Path to input text file
            output_file: Optional output JSON file path
            
        Returns:
            Dictionary with processed book data
        """
        # Parse the book structure
        book = parse_book(filepath)
        
        # Build clean JSON structure
        clean_data = {
            'metadata': self._enhance_metadata(book.metadata, filepath),
            'chapters': [],
            'statistics': {}
        }
        
        # Process chapters
        total_sentences = 0
        total_words = 0
        
        for section in book.content_sections:
            if section.type == SectionType.CHAPTER:
                chapter_data = self._process_chapter(section)
                clean_data['chapters'].append(chapter_data)
                
                total_sentences += chapter_data['sentence_count']
                total_words += chapter_data['word_count']
        
        # Add statistics
        clean_data['statistics'] = {
            'total_chapters': len(clean_data['chapters']),
            'total_sentences': total_sentences,
            'total_words': total_words,
            'average_sentences_per_chapter': total_sentences // len(clean_data['chapters']) if clean_data['chapters'] else 0,
            'average_words_per_chapter': total_words // len(clean_data['chapters']) if clean_data['chapters'] else 0
        }
        
        # Save if output file specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, indent=2, ensure_ascii=False)
        
        return clean_data
    
    def _enhance_metadata(self, metadata: Dict[str, Any], filepath: str) -> Dict[str, Any]:
        """Enhance metadata with additional information."""
        enhanced = metadata.copy()
        
        # Add processing metadata
        enhanced['source_file'] = Path(filepath).name
        enhanced['processing_note'] = 'Parsed and cleaned for gender transformation'
        enhanced['format_version'] = '2.0'
        
        # Try to extract title/author from filename if missing
        if not enhanced.get('title'):
            filename = Path(filepath).stem
            # Remove pg number prefix
            match = re.match(r'^pg\d+-(.+)$', filename)
            if match:
                title = match.group(1).replace('_', ' ')
                # Clean up common suffixes
                title = re.sub(r'\s+Complete$', '', title)
                title = re.sub(r'\s+by\s+.+$', '', title)
                enhanced['title'] = title
        
        return enhanced
    
    def _process_chapter(self, section: Section) -> Dict[str, Any]:
        """Process a chapter section into clean format."""
        # Clean the content
        content = self._clean_text(section.content)
        
        # Split into sentences
        sentences = self.splitter.split_sentences(content)
        
        # Remove chapter header from sentences if present
        if sentences and section.title:
            # Check if first sentences are the chapter header
            header_parts = section.title.split()
            if sentences[0] in header_parts or sentences[0] == section.title:
                sentences = sentences[1:]
            
            # Also check for split header (e.g., "CHAPTER", "I")
            if len(sentences) > 1 and sentences[0] + ' ' + sentences[1] == section.title:
                sentences = sentences[2:]
        
        # Calculate statistics
        word_count = sum(len(s.split()) for s in sentences)
        
        return {
            'number': section.number or 'Unknown',
            'title': section.title or f'Chapter {section.number}',
            'sentences': sentences,
            'sentence_count': len(sentences),
            'word_count': word_count
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean text for processing."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common issues
        text = text.replace('_', '')  # Remove emphasis markers
        text = re.sub(r'\[.*?\]', '', text)  # Remove brackets
        text = re.sub(r'\{.*?\}', '', text)  # Remove braces
        
        # Fix quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # Remove page numbers and headers
        text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
        
        return text.strip()


def process_all_books(
    input_dir: str = "gutenberg_texts",
    output_dir: str = "clean_json_books",
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process all books in a directory.
    
    Args:
        input_dir: Directory with text files
        output_dir: Directory for JSON output
        limit: Optional limit on number of books to process
        
    Returns:
        Summary statistics
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    processor = BookToCleanJSON()
    
    # Get all text files
    text_files = sorted(input_path.glob("*.txt"))
    if limit:
        text_files = text_files[:limit]
    
    print(f"Processing {len(text_files)} books...")
    print("-" * 60)
    
    stats = {
        'total': 0,
        'successful': 0,
        'failed': 0,
        'total_chapters': 0,
        'total_sentences': 0,
        'total_words': 0
    }
    
    for i, filepath in enumerate(text_files):
        print(f"[{i+1}/{len(text_files)}] {filepath.name}...", end=" ")
        
        try:
            # Process book
            output_file = output_path / f"{filepath.stem}_clean.json"
            data = processor.process_book(str(filepath), str(output_file))
            
            # Update stats
            stats['successful'] += 1
            stats['total_chapters'] += data['statistics']['total_chapters']
            stats['total_sentences'] += data['statistics']['total_sentences']
            stats['total_words'] += data['statistics']['total_words']
            
            print(f"✓ {data['statistics']['total_chapters']} chapters")
            
        except Exception as e:
            stats['failed'] += 1
            print(f"✗ ERROR: {str(e)[:50]}")
        
        stats['total'] += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Total books: {stats['total']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"\nTotal chapters: {stats['total_chapters']:,}")
    print(f"Total sentences: {stats['total_sentences']:,}")
    print(f"Total words: {stats['total_words']:,}")
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert Gutenberg books to clean JSON format"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Input file or directory (default: process all)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file or directory"
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        help="Limit number of books to process"
    )
    
    args = parser.parse_args()
    
    if args.input:
        if Path(args.input).is_file():
            # Process single file
            processor = BookToCleanJSON()
            output = args.output or args.input.replace('.txt', '_clean.json')
            data = processor.process_book(args.input, output)
            
            print(f"Processed: {data['metadata'].get('title', 'Unknown')}")
            print(f"Chapters: {data['statistics']['total_chapters']}")
            print(f"Sentences: {data['statistics']['total_sentences']:,}")
            print(f"Words: {data['statistics']['total_words']:,}")
        else:
            # Process directory
            output_dir = args.output or "clean_json_books"
            process_all_books(args.input, output_dir, args.limit)
    else:
        # Process all
        process_all_books(limit=args.limit)