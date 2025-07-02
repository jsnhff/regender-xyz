"""Main book parser API"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import re

from .patterns import PatternRegistry, PatternType
from .detectors import SectionDetector
from .detectors.section_detector import DetectedSection


class BookParser:
    """
    Main parser class that converts books to JSON format
    
    Usage:
        parser = BookParser()
        book_data = parser.parse_file("book.txt")
        # or
        book_data = parser.parse_text(text_content)
    """
    
    def __init__(self):
        self.pattern_registry = PatternRegistry()
        self.section_detector = SectionDetector(self.pattern_registry)
        
        # Common abbreviations that don't end sentences
        self.abbreviations = {
            'Mr', 'Mrs', 'Ms', 'Dr', 'Prof', 'Rev', 'Sr', 'Jr', 
            'Lt', 'Col', 'Gen', 'Capt', 'Sgt', 'Corp', 'Pvt',
            'Inc', 'Ltd', 'Co', 'Corp',
            'Jan', 'Feb', 'Mar', 'Apr', 'Jun', 'Jul', 'Aug', 'Sep', 'Sept', 'Oct', 'Nov', 'Dec',
            'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun',
            'St', 'Ave', 'Rd', 'Blvd', 'Ln', 'Ct',
            'vs', 'etc'
        }
    
    def parse_file(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse a book file"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        
        return self.parse_text(text, options)
    
    def parse_text(self, text: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse book text"""
        if options is None:
            options = {}
        
        # Split into lines
        lines = text.split('\n')
        
        # Extract metadata
        metadata = self._extract_metadata(lines[:100])  # Check first 100 lines
        
        # Detect sections
        sections = self.section_detector.detect_sections(
            lines,
            detect_frontmatter=options.get('detect_frontmatter', True),
            min_section_lines=options.get('min_section_lines', 5)
        )
        
        # Convert sections to chapters format
        chapters = self._sections_to_chapters(sections, lines)
        
        # If no chapters detected, treat entire text as one chapter
        if not chapters:
            # Clean the entire text
            full_text = '\n'.join(lines)
            cleaned_text = self._clean_content(full_text)
            paragraphs = self._split_paragraphs(cleaned_text)
            
            if paragraphs:
                all_sentences = []
                for para in paragraphs:
                    all_sentences.extend(para['sentences'])
                
                chapters = [{
                    "number": "1",
                    "title": "",
                    "type": "chapter",
                    "paragraphs": paragraphs,
                    "sentence_count": len(all_sentences),
                    "word_count": sum(len(s.split()) for s in all_sentences)
                }]
        
        # Calculate statistics
        statistics = self._calculate_statistics(chapters)
        
        return {
            "metadata": metadata,
            "chapters": chapters,
            "statistics": statistics
        }
    
    def _extract_metadata(self, lines: List[str]) -> Dict[str, str]:
        """Extract book metadata from initial lines"""
        metadata = {
            "title": "Unknown",
            "author": "Unknown",
            "date": "",
            "source": "Unknown",
            "processing_note": "Parsed with modular book parser",
            "format_version": "2.0"
        }
        
        # Common patterns
        title_pattern = re.compile(r'Title:\s*(.+)', re.IGNORECASE)
        author_pattern = re.compile(r'Author:\s*(.+)', re.IGNORECASE)
        date_pattern = re.compile(r'(?:Release Date:|Date:)\s*(.+)', re.IGNORECASE)
        
        for line in lines:
            # Title
            match = title_pattern.search(line)
            if match:
                metadata["title"] = match.group(1).strip()
                continue
            
            # Author
            match = author_pattern.search(line)
            if match:
                metadata["author"] = match.group(1).strip()
                continue
            
            # Date
            match = date_pattern.search(line)
            if match:
                metadata["date"] = match.group(1).strip()
                continue
            
            # Project Gutenberg
            if "Project Gutenberg" in line:
                metadata["source"] = "Project Gutenberg"
        
        return metadata
    
    def _sections_to_chapters(self, sections: List[DetectedSection], 
                             all_lines: List[str]) -> List[Dict[str, Any]]:
        """Convert detected sections to chapter format"""
        chapters = []
        
        # Filter to only content sections
        content_sections = [s for s in sections if s.pattern_type in [
            PatternType.CHAPTER, PatternType.ACT, PatternType.SCENE,
            PatternType.LETTER, PatternType.STORY, PatternType.LIVRE,
            PatternType.EPILOGUE, PatternType.PROLOGUE
        ]]
        
        for i, section in enumerate(content_sections):
            # Get section content
            if section.content_lines:
                content = '\n'.join(section.content_lines)
            else:
                # Extract content from line numbers
                start = section.start_line + 1  # Skip header line
                end = section.end_line if section.end_line else len(all_lines)
                if i + 1 < len(content_sections):
                    end = min(end, content_sections[i + 1].start_line)
                content = '\n'.join(all_lines[start:end])
            
            # Clean content
            content = self._clean_content(content)
            
            # Split into paragraphs first, then sentences
            paragraphs = self._split_paragraphs(content)
            
            # Calculate statistics
            all_sentences = []
            for para in paragraphs:
                all_sentences.extend(para['sentences'])
            
            # Create chapter entry
            chapter = {
                "number": section.number or str(i + 1),
                "title": section.title or "",
                "type": section.pattern_type.value,
                "paragraphs": paragraphs,
                "sentence_count": len(all_sentences),
                "word_count": sum(len(s.split()) for s in all_sentences)
            }
            
            chapters.append(chapter)
        
        return chapters
    
    def _clean_content(self, content: str) -> str:
        """Clean section content"""
        # Remove illustration markers
        content = re.sub(r'\[Illustration:?[^\]]*\]', '', content, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove page numbers
        content = re.sub(r'Page\s+\d+', '', content, flags=re.IGNORECASE)
        content = re.sub(r'-{0,2}\s*\d+\s*-{0,2}(?=\s|$)', '', content)
        
        # Remove formatting artifacts
        content = re.sub(r'/\s*[A-Z]{3,}', '', content)
        
        # Fix spacing while preserving paragraph breaks
        # First, normalize paragraph breaks to double newlines
        content = re.sub(r'\n\s*\n+', '\n\n', content)
        
        # Fix spacing around punctuation
        content = re.sub(r'\s+([.!?,;:])', r'\1', content)
        content = re.sub(r'([.!?])\s*([a-z])', r'\1 \2', content)
        
        # Collapse multiple spaces (but not newlines) into single spaces
        content = re.sub(r'[^\S\n]+', ' ', content)
        
        # Remove orphan brackets
        content = re.sub(r'(?<!\[)\]', '', content)
        content = re.sub(r'\[(?!\])', '', content)
        
        return content.strip()
    
    def _split_paragraphs(self, text: str) -> List[Dict[str, List[str]]]:
        """Split text into paragraphs, preserving sentence structure within each"""
        if not text:
            return []
        
        # First, normalize line breaks within paragraphs (unwrap soft line breaks)
        # Replace single newlines with spaces, but preserve double newlines
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        
        # Now split on actual paragraph breaks (2+ newlines)
        paragraph_splits = re.split(r'\n\s*\n+', text)
        
        paragraphs = []
        for para_text in paragraph_splits:
            para_text = para_text.strip()
            if para_text:  # Skip empty paragraphs
                sentences = self._split_sentences(para_text)
                if sentences:  # Only add paragraphs that have sentences
                    paragraphs.append({
                        "sentences": sentences
                    })
        
        return paragraphs
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences with proper handling of abbreviations"""
        if not text:
            return []
        
        # First, mark abbreviations to protect them
        protected_text = text
        for abbr in self.abbreviations:
            # Replace periods after abbreviations with a placeholder
            protected_text = re.sub(
                rf'\b{re.escape(abbr)}\.',
                f'{abbr}<<<ABBR_DOT>>>',
                protected_text,
                flags=re.IGNORECASE
            )
        
        # Also protect ellipses
        protected_text = re.sub(r'\.\.\.', '<<<ELLIPSIS>>>', protected_text)
        protected_text = re.sub(r'\.\.', '<<<DOUBLE_DOT>>>', protected_text)
        
        # Now split on sentence boundaries
        # More sophisticated pattern that handles edge cases better
        # Split on: sentence-ending punctuation followed by space and capital letter,
        # or followed by closing quote and space, or followed by newlines
        sentences = re.split(
            r'(?<=[.!?])\s+(?=[A-Z])|'  # Period + space + capital
            r'(?<=[.!?]")\s+|'          # Period + quote + space
            r'(?<=[.!?])\s*\n+',        # Period + newline(s)
            protected_text
        )
        
        # Restore protected elements and clean
        cleaned = []
        for sent in sentences:
            # Restore periods and ellipses
            sent = sent.replace('<<<ABBR_DOT>>>', '.')
            sent = sent.replace('<<<ELLIPSIS>>>', '...')
            sent = sent.replace('<<<DOUBLE_DOT>>>', '..')
            sent = sent.strip()
            
            # Skip very short fragments, but keep short complete sentences
            # Check if it's a title (all caps) or has proper sentence structure
            if sent and (len(sent) > 5 or sent.isupper() or re.match(r'^[A-Z].*[.!?]$', sent)):
                cleaned.append(sent)
        
        return cleaned
    
    def _calculate_statistics(self, chapters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate book statistics"""
        total_chapters = len(chapters)
        total_sentences = sum(ch['sentence_count'] for ch in chapters)
        total_words = sum(ch['word_count'] for ch in chapters)
        total_paragraphs = sum(len(ch.get('paragraphs', [])) for ch in chapters)
        
        return {
            "total_chapters": total_chapters,
            "total_paragraphs": total_paragraphs,
            "total_sentences": total_sentences,
            "total_words": total_words,
            "average_sentences_per_chapter": total_sentences / total_chapters if total_chapters > 0 else 0,
            "average_paragraphs_per_chapter": total_paragraphs / total_chapters if total_chapters > 0 else 0,
            "average_sentences_per_paragraph": total_sentences / total_paragraphs if total_paragraphs > 0 else 0,
            "average_words_per_sentence": total_words / total_sentences if total_sentences > 0 else 0
        }
    
    def register_patterns(self, patterns: List):
        """Register additional patterns"""
        self.pattern_registry.register_patterns(patterns)
    
    def clear_patterns(self):
        """Clear all patterns"""
        self.pattern_registry.clear_patterns()
    
    def get_pattern_summary(self) -> Dict[str, int]:
        """Get summary of registered patterns"""
        return self.pattern_registry.get_pattern_summary()
    
    def parse_file_to_json(self, input_file: str, output_file: str) -> Dict[str, Any]:
        """Parse a file and save to JSON."""
        from .formatters import save_book_json
        book_data = self.parse_file(input_file)
        save_book_json(book_data, output_file)
        return book_data