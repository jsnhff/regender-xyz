#!/usr/bin/env python3
"""
book_to_json.py - Complete book preprocessing pipeline in a single file.

This module converts text books into clean JSON format with:
- Chapter detection
- Artifact removal
- Sentence splitting
- Dialogue handling

Usage:
    from book_to_json import process_book_to_json
    
    # Process a book
    book_data = process_book_to_json("book.txt", "book_clean.json")
    
    # Access the data
    for chapter in book_data['chapters']:
        for sentence in chapter['sentences']:
            # Process sentence
"""

import re
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Try to import CLI visuals if available
try:
    from cli_visuals import print_info, print_success, print_error, print_warning
    CLI_VISUALS_AVAILABLE = True
except ImportError:
    CLI_VISUALS_AVAILABLE = False


# ============================================================================
# Data Classes
# ============================================================================

class SectionType(Enum):
    """Types of book sections"""
    FRONTMATTER = "frontmatter"
    TOC = "toc"
    CHAPTER = "chapter"
    EPILOGUE = "epilogue"
    APPENDIX = "appendix"
    ETYMOLOGY = "etymology"
    EXTRACTS = "extracts"
    UNKNOWN = "unknown"


@dataclass
class BookSection:
    """A section of a book (chapter, frontmatter, etc)"""
    type: SectionType
    content: str
    start_pos: int
    end_pos: int
    title: Optional[str] = None
    number: Optional[str] = None


@dataclass
class CanonicalBook:
    """Canonical book format with metadata and sections"""
    metadata: Dict[str, str] = field(default_factory=dict)
    sections: List[BookSection] = field(default_factory=list)


# ============================================================================
# Chapter Detection Patterns
# ============================================================================

class ChapterPatterns:
    """Collection of chapter detection patterns"""
    
    # Roman numeral components
    ROMAN = r'[IVXLCDM]+'
    
    # Number words
    NUMBER_WORDS = r'(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|' \
                   r'Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|' \
                   r'Eighteen|Nineteen|Twenty|Thirty|Forty|Fifty|Sixty|Seventy|' \
                   r'Eighty|Ninety|Hundred)'
    
    # Common chapter patterns - ORDERED BY SPECIFICITY
    PATTERNS = [
        # Most specific first - with titles
        (r'^CHAPTER\s+(\d+)\.\s+(.+)$', 'arabic_titled'),
        (r'^Chapter\s+(\d+)\.\s+(.+)$', 'arabic_titled'),
        (r'^CHAPTER\s+(' + ROMAN + r')\.\s+(.+)$', 'roman_titled'),
        (r'^Chapter\s+(' + ROMAN + r')\.\s+(.+)$', 'roman_titled'),
        
        # With separators
        (r'^Chapter\s+(' + ROMAN + r')\s*[:\-—]\s*(.+)$', 'roman_titled'),
        (r'^CHAPTER\s+(' + ROMAN + r')\s*[:\-—]\s*(.+)$', 'roman_titled'),
        (r'^Chapter\s+(\d+)\s*[:\-—]\s*(.+)$', 'arabic_titled'),
        (r'^CHAPTER\s+(\d+)\s*[:\-—]\s*(.+)$', 'arabic_titled'),
        
        # Chapter number only
        (r'^Chapter\s+(' + ROMAN + r')\.?\s*$', 'roman'),
        (r'^CHAPTER\s+(' + ROMAN + r')\.?\s*$', 'roman'),
        (r'^Chapter\s+(\d+)\.?\s*$', 'arabic'),
        (r'^CHAPTER\s+(\d+)\.?\s*$', 'arabic'),
        (r'^Chapter\s+(' + NUMBER_WORDS + r')\s*$', 'word'),
        (r'^CHAPTER\s+(' + NUMBER_WORDS + r')\s*$', 'word'),
        
        # Alternative formats
        (r'^(' + ROMAN + r')\.\s*$', 'roman_only'),
        (r'^(\d+)\.\s*$', 'arabic_only'),  # Most generic - last
        (r'^Part\s+(' + ROMAN + r')\.?\s*$', 'part_roman'),
        (r'^PART\s+(' + ROMAN + r')\.?\s*$', 'part_roman'),
        (r'^Part\s+(\d+)\.?\s*$', 'part_arabic'),
        (r'^PART\s+(\d+)\.?\s*$', 'part_arabic'),
    ]


# ============================================================================
# Text Cleaning
# ============================================================================

class TextCleaner:
    """Enhanced text cleaning with artifact removal"""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        
    def clean_text(self, text: str) -> str:
        """Clean text with multiple passes for different artifact types"""
        
        # Pass 1: Remove illustration blocks and markers
        text = self._remove_illustration_markers(text)
        
        # Pass 2: Clean up orphan brackets
        text = self._remove_orphan_brackets(text)
        
        # Pass 3: Remove formatting artifacts
        text = self._remove_formatting_artifacts(text)
        
        # Pass 4: Fix punctuation issues
        text = self._fix_punctuation(text)
        
        # Pass 5: General cleanup
        text = self._general_cleanup(text)
        
        return text.strip()
    
    def _remove_illustration_markers(self, text: str) -> str:
        """Remove all illustration-related content"""
        # Remove [Illustration: ...] with any content
        text = re.sub(r'\[Illustration:?[^\]]*\]', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove standalone [Illustration] tags
        text = re.sub(r'\[Illustration\]', '', text, flags=re.IGNORECASE)
        
        return text
    
    def _remove_orphan_brackets(self, text: str) -> str:
        """Remove standalone brackets that are artifacts"""
        # Remove standalone ] or [ with surrounding whitespace
        text = re.sub(r'\s*\]\s*(?=[A-Z])', ' ', text)  # ] before capital letter
        text = re.sub(r'\s*\]\s*\.', '.', text)  # ] before period
        text = re.sub(r'(\w)\s*\]\s*(\w)', r'\1 \2', text)  # ] between words
        text = re.sub(r'\s*\[\s*(?=[A-Z])', ' ', text)  # [ before capital letter
        
        # Remove brackets at line boundaries
        text = re.sub(r'^\s*\]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*\]\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\[\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*\[\s*$', '', text, flags=re.MULTILINE)
        
        # Remove any remaining isolated brackets
        text = re.sub(r'(?<!\[)\]', '', text)  # ] without matching [
        text = re.sub(r'\[(?!\])', '', text)  # [ without matching ]
        
        return text
    
    def _remove_formatting_artifacts(self, text: str) -> str:
        """Remove formatting codes and markers"""
        # Remove formatting codes like /NIND
        text = re.sub(r'/\s*[A-Z]{3,}', '', text)
        
        # Remove isolated RIGHT/LEFT markers
        text = re.sub(r'\b(?:RIGHT|LEFT|CENTER)\b\s*(?=["\'])', '', text)
        
        # Remove page numbers and markers
        text = re.sub(r'Page\s+\d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'-{0,2}\s*\d+\s*-{0,2}(?=\s|$)', '', text)
        
        return text
    
    def _fix_punctuation(self, text: str) -> str:
        """Fix punctuation issues"""
        # Fix space before punctuation
        text = re.sub(r'\s+([.!?,;:])', r'\1', text)
        
        # Fix missing space after punctuation
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        # Fix quote issues
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('"', '"').replace('"', '"')
        
        return text
    
    def _general_cleanup(self, text: str) -> str:
        """General text cleanup"""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove extra spaces around newlines
        text = re.sub(r' *\n *', '\n', text)
        
        return text


# ============================================================================
# Sentence Splitting
# ============================================================================

class SentenceSplitter:
    """Improved sentence splitter with abbreviation and dialogue handling"""
    
    # Common abbreviations to protect
    ABBREVIATIONS = [
        'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.', 'Sr.', 'Jr.', 'Ph.D.', 'M.D.', 
        'B.A.', 'M.A.', 'D.D.S.', 'Ph.D', 'Inc.', 'Ltd.', 'Co.', 'Corp.',
        'vs.', 'etc.', 'i.e.', 'e.g.', 'cf.', 'al.', 'No.', 'Vol.',
        'Jan.', 'Feb.', 'Mar.', 'Apr.', 'Jun.', 'Jul.', 'Aug.', 'Sep.', 
        'Sept.', 'Oct.', 'Nov.', 'Dec.', 'Mon.', 'Tue.', 'Wed.', 'Thu.', 
        'Fri.', 'Sat.', 'Sun.', 'St.', 'Ave.', 'Rd.', 'Blvd.'
    ]
    
    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences with improved handling"""
        if not text:
            return []
        
        # Protect abbreviations
        protected_text = text
        for abbr in self.ABBREVIATIONS:
            protected_text = protected_text.replace(abbr, abbr.replace('.', '<!DOT!>'))
        
        # Pre-process: protect ellipsis
        protected_text = protected_text.replace('...', '<!ELLIPSIS!>')
        
        # Mark sentence boundaries
        patterns = [
            # Standard sentence ending
            (r'([.!?])\s+(?=[A-Z])', r'\1<|SPLIT|>'),
            
            # Sentence ending with quotes
            (r'([.!?]")\s+(?=[A-Z])', r'\1<|SPLIT|>'),
            (r'([.!?]")\s+(?=[A-Z])', r'\1<|SPLIT|>'),
        ]
        
        for pattern, replacement in patterns:
            protected_text = re.sub(pattern, replacement, protected_text)
        
        # Split on markers
        sentences = protected_text.split('<|SPLIT|>')
        
        # Clean up and restore
        cleaned_sentences = []
        for sentence in sentences:
            # Restore protected elements
            sentence = sentence.replace('<!DOT!>', '.')
            sentence = sentence.replace('<!ELLIPSIS!>', '...')
            
            # Clean up whitespace
            sentence = sentence.strip()
            
            # Skip empty or very short sentences
            if len(sentence) < 3:
                continue
            
            cleaned_sentences.append(sentence)
        
        return cleaned_sentences


# ============================================================================
# Long Sentence Fixer
# ============================================================================

def fix_long_sentences_with_dialogues(chapters: List[Dict[str, Any]], verbose: bool = False) -> int:
    """Fix long sentences with embedded dialogues in chapters"""
    
    def should_split_here(current_part: str, next_part: str) -> bool:
        """Determine if we should split between two parts"""
        # Always split if current ends with sentence ending
        if re.search(r'[.!?]["\"]?$', current_part.strip()):
            # And next starts with capital or quote
            if next_part and re.match(r'^[A-Z""]', next_part.strip()):
                return True
        
        # Split between complete dialogue exchanges
        if (current_part.strip().endswith('"') or current_part.strip().endswith('"')):
            if next_part.strip().startswith('"') or next_part.strip().startswith('"'):
                return True
        
        return False
    
    def smart_split_sentence(sentence: str) -> List[str]:
        """Split a sentence containing newlines into proper sentences"""
        # If no double newlines, return as is
        if '\n\n' not in sentence:
            return [sentence]
        
        # Split on double newlines
        parts = sentence.split('\n\n')
        
        # Create separate sentences
        sentences = []
        current_sentence = []
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            
            # Always add the current part
            current_sentence.append(part)
            
            # Check if we should break after this part
            if i < len(parts) - 1:
                next_part = parts[i + 1].strip() if i + 1 < len(parts) else ""
                
                if should_split_here(part, next_part):
                    # Create sentence from current parts
                    sentences.append('\n\n'.join(current_sentence))
                    current_sentence = []
        
        # Add any remaining parts
        if current_sentence:
            sentences.append('\n\n'.join(current_sentence))
        
        # Final pass - if any sentence is still too long, split more aggressively
        final_sentences = []
        for sent in sentences:
            if len(sent) > 500 and '\n\n' in sent:
                # Split every complete sentence
                subparts = sent.split('\n\n')
                for subpart in subparts:
                    if subpart.strip():
                        final_sentences.append(subpart.strip())
            else:
                final_sentences.append(sent)
        
        return final_sentences
    
    # Process chapters
    total_splits = 0
    
    for chapter in chapters:
        original_sentences = chapter['sentences']
        new_sentences = []
        chapter_splits = 0
        
        for sent_idx, sentence in enumerate(original_sentences):
            # Split long sentences or those with embedded newlines
            if len(sentence) > 500 and '\n\n' in sentence:
                split_sentences = smart_split_sentence(sentence)
                
                if len(split_sentences) > 1:
                    chapter_splits += len(split_sentences) - 1
                    
                    if verbose and chapter_splits <= 5:  # Show first few
                        print(f"\n{chapter['title']}, Sentence {sent_idx + 1}:")
                        print(f"  Original: {len(sentence)} chars")
                        print(f"  Split into: {len(split_sentences)} sentences")
                        for j, s in enumerate(split_sentences[:3]):
                            preview = s[:60] + "..." if len(s) > 60 else s
                            print(f"    {j+1}. {preview}")
                        if len(split_sentences) > 3:
                            print(f"    ... and {len(split_sentences) - 3} more")
                
                new_sentences.extend(split_sentences)
            else:
                new_sentences.append(sentence)
        
        # Update chapter
        chapter['sentences'] = new_sentences
        chapter['sentence_count'] = len(new_sentences)
        total_splits += chapter_splits
    
    return total_splits


# ============================================================================
# Main Book Parser
# ============================================================================

class BookParser:
    """Main parser for converting books to canonical format"""
    
    def __init__(self, verbose: bool = True):
        self.chapter_patterns = ChapterPatterns()
        self.verbose = verbose
    
    def parse(self, text: str) -> CanonicalBook:
        """Parse text into canonical book format"""
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Extract metadata
        metadata = self._extract_metadata(text)
        
        # Find main content boundaries
        content_start, content_end = self._find_content_boundaries(text)
        
        # Extract sections
        sections = self._extract_sections(text, content_start, content_end)
        
        return CanonicalBook(metadata=metadata, sections=sections)
    
    def _extract_metadata(self, text: str) -> Dict[str, str]:
        """Extract metadata from text"""
        metadata = {}
        
        # Title patterns
        title_patterns = [
            r'^Title:\s*(.+)$',
            r'^The Project Gutenberg [Ee]Book of (.+),',
            r'^\*\*\*\s*START.*?PROJECT GUTENBERG.*?"(.+?)"',
        ]
        
        # Author patterns
        author_patterns = [
            r'^Author:\s*(.+)$',
            r'^by\s+(.+)$',
            r'^By\s+(.+)$',
        ]
        
        # Search first 100 lines
        lines = text.split('\n')[:100]
        
        for line in lines:
            # Check title
            if 'title' not in metadata:
                for pattern in title_patterns:
                    match = re.search(pattern, line, re.MULTILINE)
                    if match:
                        metadata['title'] = match.group(1).strip()
                        break
            
            # Check author
            if 'author' not in metadata:
                for pattern in author_patterns:
                    match = re.search(pattern, line, re.MULTILINE)
                    if match:
                        metadata['author'] = match.group(1).strip()
                        break
            
            # Check for date
            if 'date' not in metadata:
                date_match = re.search(r'(?:Release Date|Posting Date):\s*(.+)$', line)
                if date_match:
                    metadata['date'] = date_match.group(1).strip()
        
        # Add source if Project Gutenberg
        if 'Project Gutenberg' in text[:1000]:
            metadata['source'] = 'Project Gutenberg'
        
        return metadata
    
    def _find_content_boundaries(self, text: str) -> Tuple[int, int]:
        """Find the boundaries of main content"""
        start = 0
        end = len(text)
        
        # Look for Project Gutenberg markers
        start_match = re.search(r'\*\*\*\s*START[^\*]+\*\*\*', text)
        if start_match:
            start = start_match.end()
        
        end_match = re.search(r'\*\*\*\s*END[^\*]+\*\*\*', text)
        if end_match:
            end = end_match.start()
        
        return start, end
    
    def _extract_sections(self, text: str, start: int, end: int) -> List[BookSection]:
        """Extract all sections from text"""
        content = text[start:end]
        sections = []
        
        # First, check for special sections (TOC, ETYMOLOGY, etc.)
        special_sections = self._find_special_sections(content, start)
        
        # Find all chapter positions
        chapter_positions = self._find_chapter_positions(content, start)
        
        # Combine all positions
        all_positions = special_sections + chapter_positions
        
        if not all_positions:
            # No sections found - treat as single section
            sections.append(BookSection(
                type=SectionType.UNKNOWN,
                content=content,
                start_pos=start,
                end_pos=end,
                title="Full Text"
            ))
            return sections
        
        # Sort by position
        all_positions.sort(key=lambda x: x[0])
        
        # Filter out any chapter markers that are within a TOC
        filtered_positions = self._filter_toc_chapters(all_positions, text)
        
        # Debug: log filtering results
        if self.verbose:
            chapters_before = sum(1 for p in all_positions if p[1] == SectionType.CHAPTER)
            chapters_after = sum(1 for p in filtered_positions if p[1] == SectionType.CHAPTER)
            print(f"[DEBUG] Chapters before TOC filtering: {chapters_before}")
            print(f"[DEBUG] Chapters after TOC filtering: {chapters_after}")
        
        # Create sections
        for i, (pos, section_type, title, number) in enumerate(filtered_positions):
            # Determine end position
            if i < len(filtered_positions) - 1:
                end_pos = filtered_positions[i + 1][0]
            else:
                end_pos = end
            
            # Extract content
            section_content = text[pos:end_pos].strip()
            
            sections.append(BookSection(
                type=section_type,
                content=section_content,
                start_pos=pos,
                end_pos=end_pos,
                title=title,
                number=str(number) if number else None
            ))
        
        # Sort chapters by number (if they have numbers)
        # Keep non-chapter sections in their original order
        chapter_sections = [s for s in sections if s.type == SectionType.CHAPTER and s.number]
        other_sections = [s for s in sections if s.type != SectionType.CHAPTER or not s.number]
        
        # Sort chapters by number
        try:
            # Try to sort numerically if possible
            chapter_sections.sort(key=lambda s: int(s.number) if s.number.isdigit() else float('inf'))
        except:
            # Fallback to string sort
            chapter_sections.sort(key=lambda s: s.number)
        
        # Combine: other sections first, then sorted chapters
        sections = other_sections + chapter_sections
        
        return sections
    
    def _find_special_sections(self, text: str, offset: int) -> List[Tuple[int, SectionType, str, Any]]:
        """Find special sections like TOC, ETYMOLOGY, EXTRACTS"""
        positions = []
        
        # Special section patterns
        special_patterns = [
            (r'^CONTENTS\.?$', SectionType.TOC, 'CONTENTS'),
            (r'^ETYMOLOGY\.?$', SectionType.ETYMOLOGY, 'ETYMOLOGY'),
            (r'^EXTRACTS\s*\(.*\)\.?$', SectionType.EXTRACTS, 'EXTRACTS'),
            (r'^TABLE OF CONTENTS\.?$', SectionType.TOC, 'TABLE OF CONTENTS'),
        ]
        
        # Use regex to find positions directly in the text
        for pattern, section_type, title in special_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                positions.append((match.start() + offset, section_type, title, None))
        
        return positions
    
    def _filter_toc_chapters(self, positions: List[Tuple[int, SectionType, str, Any]], text: str) -> List[Tuple[int, SectionType, str, Any]]:
        """Filter out chapter markers that are within a TOC section"""
        filtered = []
        
        # Simple approach: find where chapters stop being close together
        # In a TOC, chapters are listed one after another with minimal text between
        # Real chapters have substantial content between them
        
        chapter_positions = [(p, t, title, n) for p, t, title, n in positions if t == SectionType.CHAPTER]
        
        if not chapter_positions:
            return positions
        
        # Find the first "real" chapter by looking for one with substantial content after it
        first_real_chapter_idx = None
        
        for i in range(len(chapter_positions)):
            pos, _, title, _ = chapter_positions[i]
            
            # Get text after this chapter marker
            if i + 1 < len(chapter_positions):
                next_chapter_pos = chapter_positions[i + 1][0]
                content_length = next_chapter_pos - pos
            else:
                # Last chapter - check if it has content
                content_length = min(1000, len(text) - pos)
            
            # Extract the content
            content = text[pos:pos + content_length]
            lines = content.strip().split('\n')
            
            # Check if this has real content (not just the next chapter listing)
            if len(lines) > 3:  # More than just title
                # Remove title lines and check remaining content
                content_after_title = '\n'.join(lines[2:]).strip()
                
                # Real content criteria:
                # 1. Has substantial text (> 200 chars)
                # 2. Doesn't immediately start with another chapter marker
                # 3. Contains prose indicators (periods, lowercase starts, etc.)
                if (len(content_after_title) > 200 and 
                    not re.match(r'^CHAPTER', content_after_title) and
                    re.search(r'[a-z]', content_after_title[:50])):  # Has lowercase (indicates prose)
                    first_real_chapter_idx = i
                    break
        
        if first_real_chapter_idx is None:
            # Couldn't determine, keep all chapters
            return positions
        
        # Get position of first real chapter
        first_real_pos = chapter_positions[first_real_chapter_idx][0]
        
        if self.verbose:
            print(f"[DEBUG] First real chapter at position {first_real_pos}")
            print(f"[DEBUG] Filtering out {first_real_chapter_idx} TOC chapter entries")
        
        # Filter out chapters before the first real one, but keep all other sections
        for pos, section_type, title, number in positions:
            if section_type == SectionType.CHAPTER and pos < first_real_pos:
                continue  # Skip TOC chapter entries
            filtered.append((pos, section_type, title, number))
        
        return filtered
    
    def _find_chapter_positions(self, text: str, offset: int) -> List[Tuple[int, SectionType, str, Any]]:
        """Find all chapter positions in text"""
        positions = []
        
        # Use multiline regex to find all chapter patterns
        for pattern, pattern_type in self.chapter_patterns.PATTERNS:
            # Add multiline flag to pattern
            regex = re.compile('^' + pattern, re.MULTILINE)
            
            for match in regex.finditer(text):
                # Extract chapter number and title
                if 'titled' in pattern_type:
                    number = match.group(1)
                    title = match.group(0).strip()
                else:
                    number = match.group(1)
                    title = match.group(0).strip()
                
                # Calculate absolute position
                abs_pos = match.start() + offset
                
                positions.append((abs_pos, SectionType.CHAPTER, title, number))
        
        # Sort by position
        positions.sort(key=lambda x: x[0])
        
        # Deduplicate chapters at the same position (different patterns matching same line)
        deduped = []
        seen_positions = set()
        
        for pos, section_type, title, number in positions:
            if pos not in seen_positions:
                seen_positions.add(pos)
                deduped.append((pos, section_type, title, number))
        
        return deduped


# ============================================================================
# Main Processing Function
# ============================================================================

def process_book_to_json(
    input_file: str, 
    output_file: Optional[str] = None,
    fix_long_sentences: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Process a book file into clean JSON format.
    
    Args:
        input_file: Path to the input text file
        output_file: Optional path for the output JSON file
        fix_long_sentences: Whether to split long sentences with embedded dialogues
        verbose: Whether to print progress messages
        
    Returns:
        The processed book data as a dictionary
    """
    start_time = time.time()
    
    def _log(message: str, level: str = "info"):
        """Log a message"""
        if not verbose:
            return
            
        if CLI_VISUALS_AVAILABLE:
            if level == "success":
                print_success(message)
            elif level == "warning":
                print_warning(message)
            elif level == "error":
                print_error(message)
            else:
                print_info(message)
        else:
            print(message)
    
    # Load text
    _log(f"Processing book: {input_file}")
    _log("Loading text file...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Parse chapters
    _log("Detecting chapters...")
    parser = BookParser(verbose=verbose)
    canonical_book = parser.parse(text)
    
    # Debug: show all sections found
    section_types = {}
    for s in canonical_book.sections:
        section_types[s.type.value] = section_types.get(s.type.value, 0) + 1
    
    _log(f"Found sections: {section_types}")
    
    chapter_count = sum(1 for s in canonical_book.sections if s.type == SectionType.CHAPTER)
    _log(f"Detected {chapter_count} chapters", "success")
    
    # Clean and split sentences
    _log("Cleaning text and splitting sentences...")
    cleaner = TextCleaner(verbose=False)
    splitter = SentenceSplitter()
    
    chapters = []
    total_sentences = 0
    total_words = 0
    
    for section in canonical_book.sections:
        if section.type != SectionType.CHAPTER:
            continue
        
        # Clean the text
        cleaned_text = cleaner.clean_text(section.content)
        
        # Split into sentences
        sentences = splitter.split_sentences(cleaned_text)
        
        # Count words
        word_count = sum(len(sentence.split()) for sentence in sentences)
        
        chapters.append({
            "number": section.number or str(len(chapters) + 1),
            "title": section.title,
            "sentences": sentences,
            "sentence_count": len(sentences),
            "word_count": word_count
        })
        
        total_sentences += len(sentences)
        total_words += word_count
    
    # Create book data
    book_data = {
        "metadata": {
            "title": canonical_book.metadata.get("title", "Unknown"),
            "author": canonical_book.metadata.get("author", "Unknown"),
            "date": canonical_book.metadata.get("date", ""),
            "source": canonical_book.metadata.get("source", "Unknown"),
            "processing_note": "Cleaned with artifact removal and sentence splitting",
            "format_version": "1.0"
        },
        "chapters": chapters,
        "statistics": {
            "total_chapters": len(chapters),
            "total_sentences": total_sentences,
            "total_words": total_words,
            "average_sentences_per_chapter": total_sentences // len(chapters) if chapters else 0,
            "average_words_per_sentence": total_words // total_sentences if total_sentences else 0
        }
    }
    
    _log(f"Initial processing complete: {total_sentences} sentences", "success")
    
    # Fix long sentences if requested
    if fix_long_sentences:
        _log("Checking for long sentences with embedded dialogues...")
        splits = fix_long_sentences_with_dialogues(book_data['chapters'], verbose=verbose)
        
        if splits > 0:
            # Recalculate statistics
            total_sentences = sum(ch['sentence_count'] for ch in book_data['chapters'])
            book_data['statistics']['total_sentences'] = total_sentences
            book_data['statistics']['processing_notes'] = {
                "sentence_splitting": f"Split {splits} embedded dialogues"
            }
            _log(f"Split {splits} embedded dialogues", "success")
    
    # Save if output file specified
    if output_file:
        _log(f"Saving to {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(book_data, f, indent=2, ensure_ascii=False)
        _log(f"Saved clean JSON to {output_file}", "success")
    
    # Final stats
    elapsed = time.time() - start_time
    _log(f"Processing complete in {elapsed:.1f} seconds", "success")
    _log("Final statistics:")
    _log(f"  - Chapters: {book_data['statistics']['total_chapters']}")
    _log(f"  - Sentences: {book_data['statistics']['total_sentences']}")
    _log(f"  - Words: {book_data['statistics']['total_words']}")
    
    return book_data


def recreate_text_from_json(json_file: str, output_file: Optional[str] = None) -> str:
    """
    Recreate the original text from a clean JSON file.
    
    Args:
        json_file: Path to the JSON file
        output_file: Optional path to save the recreated text
        
    Returns:
        The recreated text
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        book_data = json.load(f)
    
    # Recreate the text
    parts = []
    for chapter in book_data['chapters']:
        # Add chapter title
        parts.append(f"\n{chapter['title']}\n")
        
        # Add sentences with proper spacing
        chapter_text = ' '.join(chapter['sentences'])
        
        # Restore paragraph breaks where we have \n\n in sentences
        chapter_text = chapter_text.replace('\\n\\n', '\n\n')
        
        parts.append(chapter_text)
    
    recreated_text = '\n'.join(parts)
    
    # Save if requested
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(recreated_text)
    
    return recreated_text


# ============================================================================
# Convenience Functions for CLI Integration
# ============================================================================

class BookProcessorIntegration:
    """Integration class for backward compatibility"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    def process_book_to_json(self, input_file: str, output_file: Optional[str] = None,
                           fix_long_sentences: bool = True) -> Dict[str, Any]:
        """Process a book to JSON format"""
        return process_book_to_json(input_file, output_file, fix_long_sentences, self.verbose)
    
    def recreate_text_from_json(self, json_file: str, output_file: Optional[str] = None) -> str:
        """Recreate text from JSON"""
        return recreate_text_from_json(json_file, output_file)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert book text to clean JSON format")
    parser.add_argument("input_file", help="Input text file")
    parser.add_argument("-o", "--output", help="Output JSON file", default=None)
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress progress messages")
    parser.add_argument("--no-fix-sentences", action="store_true", 
                       help="Skip splitting embedded dialogues")
    
    args = parser.parse_args()
    
    input_file = args.input_file
    output_file = args.output
    
    try:
        book_data = process_book_to_json(
            input_file, 
            output_file, 
            fix_long_sentences=not args.no_fix_sentences,
            verbose=not args.quiet
        )
        if not args.quiet:
            print(f"\nProcessed {book_data['statistics']['total_chapters']} chapters")
            print(f"Total sentences: {book_data['statistics']['total_sentences']:,}")
            print(f"Total words: {book_data['statistics']['total_words']:,}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)