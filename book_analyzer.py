from dataclasses import dataclass
from typing import List, Optional, Dict
import re
import tiktoken
import json
from main import openai_client
from character_analysis import Character, find_characters, Mention

@dataclass
class ChapterMark:
    """Represents a chapter boundary in the text."""
    start_pos: int
    end_pos: int
    number: int
    title: str
    confidence: float = 1.0  # 1.0 for regex matches, variable for AI

@dataclass
class TextChunk:
    """A chunk of text with associated chapter information."""
    text: str
    start_pos: int
    end_pos: int
    chapters: List[ChapterMark]

class BookAnalyzer:
    """Analyzes book text to identify structure and content."""
    
    def __init__(self, config):
        self.config = config
        self.tokenizer = tiktoken.encoding_for_model(config.model_name)
        # Common chapter heading patterns
        self.chapter_patterns = [
            r'(?i)^chapter\s+([IVXLCDM]+|\d+)',  # Chapter 1 or Chapter I
            r'(?i)^(?:chapter|volume)\s+([IVXLCDM]+|\d+)[:\.]?\s*([^\n]+)?',  # Chapter 1: Title
            r'(?m)^\s*([IVXLCDM]+|\d+)\s*$',  # Just the number on its own line
        ]
    
    def create_chunks(self, text: str) -> List[TextChunk]:
        """Split text into optimal chunks for analysis, respecting chapter boundaries."""
        chapters = self._find_chapters(text)
        tokens = self._count_tokens(text)
        
        if tokens <= self.config.max_tokens_per_chunk:
            return [TextChunk(text, 0, len(text), chapters)]
            
        chunks = []
        chunk_size = self.config.max_tokens_per_chunk
        overlap = self.config.overlap_tokens
        max_chunk_tokens = int(chunk_size * 1.2)  # Allow 20% overflow for chapter alignment
        
        # Create chunks aligned with chapters
        current_pos = 0
        current_chapters = []
        chunk_start = 0
        
        for chapter in chapters:
            # If this chapter would exceed max size, create a chunk
            chapter_text = text[chapter.start_pos:] if chapter == chapters[-1] else \
                          text[chapter.start_pos:chapters[chapters.index(chapter)+1].start_pos]
            chapter_tokens = self._count_tokens(chapter_text)
            
            if current_pos + chapter_tokens > max_chunk_tokens and current_chapters:
                # Create chunk with accumulated chapters
                chunk_text = text[chunk_start:chapter.start_pos]
                chunks.append(TextChunk(
                    text=chunk_text,
                    start_pos=chunk_start,
                    end_pos=chapter.start_pos,
                    chapters=current_chapters.copy()
                ))
                
                # Start new chunk
                chunk_start = current_chapters[-1].start_pos  # Overlap at chapter boundary
                current_pos = self._count_tokens(text[chunk_start:chapter.start_pos])
                current_chapters = [current_chapters[-1]]  # Keep last chapter for overlap
            
            current_chapters.append(chapter)
            current_pos += chapter_tokens
            
            # If this is the last chapter or we've exceeded normal chunk size
            if chapter == chapters[-1] or current_pos >= chunk_size:
                end_pos = len(text) if chapter == chapters[-1] else chapters[chapters.index(chapter)+1].start_pos
                chunk_text = text[chunk_start:end_pos]
                
                chunks.append(TextChunk(
                    text=chunk_text,
                    start_pos=chunk_start,
                    end_pos=end_pos,
                    chapters=current_chapters
                ))
                
                if chapter != chapters[-1]:
                    # Start new chunk with overlap
                    chunk_start = chapter.start_pos
                    current_pos = self._count_tokens(text[chunk_start:end_pos])
                    current_chapters = [chapter]
        
        return chunks[:self.config.max_chunks_per_book]
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using model's tokenizer."""
        return len(self.tokenizer.encode(text))
    
    def _extract_chunk(self, text: str, start_token: int, chunk_size: int) -> str:
        """Extract a chunk of text based on token positions."""
        tokens = self.tokenizer.encode(text)
        start_char = len(self.tokenizer.decode(tokens[:start_token]))
        end_char = len(self.tokenizer.decode(tokens[:start_token + chunk_size]))
        
        # Adjust to sentence boundaries
        chunk = text[start_char:end_char]
        while end_char < len(text) and text[end_char-1] not in '.!?':
            end_char += 1
        while start_char > 0 and text[start_char-1] not in '.!?':
            start_char -= 1
            
        return text[start_char:end_char].strip()
    
    def _find_chapters(self, text: str) -> List[ChapterMark]:
        """Find chapter boundaries using regex first, AI if needed."""
        chapters = self._find_chapters_regex(text)
        
        if self._needs_ai_analysis(chapters, text):
            ai_chapters = self._find_chapters_ai(text)
            return ai_chapters if ai_chapters else chapters
            
        return chapters
    
    def _find_chapters_regex(self, text: str) -> List[ChapterMark]:
        """Find chapter boundaries using regex patterns."""
        chapters = []
        lines = text.split('\n')
        pos = 0
        
        for i, line in enumerate(lines):
            for pattern in self.chapter_patterns:
                match = re.match(pattern, line.strip())
                if match:
                    num_str = match.group(1)
                    try:
                        number = int(num_str)
                    except ValueError:
                        number = self._roman_to_int(num_str)
                    
                    title = match.group(2) if len(match.groups()) > 1 else ""
                    start = pos
                    end = pos + len(line)
                    
                    chapters.append(ChapterMark(
                        start_pos=start,
                        end_pos=end,
                        number=number,
                        title=title or ""
                    ))
                    break
            pos += len(line) + 1
            
        return chapters
    
    def _find_chapters_ai(self, text: str) -> Optional[List[ChapterMark]]:
        """Find chapter boundaries using AI analysis."""
        prompt = """Analyze this text excerpt and identify all chapter boundaries.
Return a JSON array of chapters. Each chapter should have:
- start_text: The exact text that starts the chapter (first 50 chars)
- number: The chapter number as an integer
- title: The chapter title if present, empty string if none

Example response:
[
    {"start_text": "Chapter 1: A Truth Universally Acknowledged", "number": 1, "title": "A Truth Universally Acknowledged"},
    {"start_text": "Chapter 2", "number": 2, "title": ""}
]

Focus on:
- Traditional chapter markers (Chapter X, Volume Y)
- Scene breaks with clear numbering
- Section numbers that indicate chapters
- Chapter titles or headings

Be precise with start_text as it's used to locate the chapter position.
Only mark clear chapter boundaries, not scene breaks or minor transitions."""

        try:
            # Prepare messages
            messages = [
                {"role": "system", "content": "You are a precise literary analyzer focused on identifying chapter structure in books."},
                {"role": "user", "content": f"{prompt}\n\nText to analyze:\n{text[:50000]}"}  # First 50k chars
            ]
            
            # Get AI response
            response = openai_client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                temperature=0.1,  # Low temperature for consistency
                max_tokens=2000
            )
            
            # Parse response
            try:
                chapters_data = json.loads(response.choices[0].message.content)
                if not isinstance(chapters_data, list):
                    return None
                    
                # Convert to ChapterMarks
                chapters = []
                for ch in chapters_data:
                    # Find position of start_text
                    start_text = ch['start_text'][:50]  # Limit length for search
                    pos = text.find(start_text)
                    if pos == -1:
                        continue
                        
                    chapters.append(ChapterMark(
                        start_pos=pos,
                        end_pos=pos + len(start_text),
                        number=int(ch['number']),
                        title=ch.get('title', ''),
                        confidence=0.9  # AI-detected chapters get 0.9 confidence
                    ))
                
                # Validate and sort chapters
                if not chapters or not self._validate_chapters(chapters):
                    return None
                    
                return sorted(chapters, key=lambda x: x.start_pos)
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error parsing AI response: {e}")
                return None
                
        except Exception as e:
            print(f"AI analysis failed: {e}")
            return None
            
    def _needs_ai_analysis(self, chapters: List[ChapterMark], text: str) -> bool:
        """Check if AI analysis is needed based on regex results."""
        if not chapters:
            return True
            
        # Check for sequence gaps
        numbers = [ch.number for ch in chapters]
        expected = list(range(min(numbers), max(numbers) + 1))
        if numbers != expected:
            return True
            
        # Check for suspiciously large gaps
        chapter_sizes = []
        for i in range(len(chapters) - 1):
            size = chapters[i+1].start_pos - chapters[i].start_pos
            chapter_sizes.append(size)
            
        if chapter_sizes:
            avg_size = sum(chapter_sizes) / len(chapter_sizes)
            max_size = max(chapter_sizes)
            if max_size > avg_size * self.config.max_chapter_size_ratio:
                return True
                
        # Check for consistent formatting
        titles = [bool(ch.title) for ch in chapters]
        if any(titles) and not all(titles):
            return True
            
        return False
    
    def _roman_to_int(self, roman: str) -> int:
        """Convert Roman numeral to integer."""
        values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 
                 'C': 100, 'D': 500, 'M': 1000}
        roman = roman.upper()
        result = 0
        
        for i in range(len(roman)):
            if i > 0 and values[roman[i]] > values[roman[i-1]]:
                result += values[roman[i]] - 2 * values[roman[i-1]]
            else:
                result += values[roman[i]]
                
        return result
    
    def _adjust_chunk_boundary(self, text: str, pos: int, chapters: List[ChapterMark]) -> int:
        """Adjust chunk boundary to nearest chapter if within threshold."""
        threshold = 5000  # characters
        
        for chapter in chapters:
            if abs(chapter.start_pos - pos) < threshold:
                return chapter.start_pos
        return pos

    def analyze_characters(self, text: str) -> Dict[str, Character]:
        """Analyze characters across the entire book using chunked analysis."""
        chunks = self.create_chunks(text)
        all_characters: Dict[str, Character] = {}
        
        print(f"Analyzing {len(chunks)} chunks for characters...")
        
        for i, chunk in enumerate(chunks):
            print(f"\nAnalyzing chunk {i+1} (Chapters {chunk.chapters[0].number}-{chunk.chapters[-1].number})...")
            
            # Split chunk into smaller sub-chunks for API limits
            # Using 40k tokens to leave room for prompt and response
            sub_chunks = self._create_sub_chunks(chunk.text, max_tokens=40000)
            print(f"Created {len(sub_chunks)} sub-chunks...")
            
            chunk_characters: Dict[str, Character] = {}
            for j, sub_chunk in enumerate(sub_chunks):
                print(f"  Analyzing sub-chunk {j+1}/{len(sub_chunks)}...")
                try:
                    sub_characters = find_characters(sub_chunk, openai_client)
                    
                    # Adjust positions to chunk-relative positions
                    sub_start = len(''.join(sub_chunks[:j]))
                    for char in sub_characters.values():
                        for mention in char.mentions:
                            adjusted_start = mention.start + sub_start
                            adjusted_end = mention.end + sub_start
                            char.mentions.remove(mention)
                            char.add_mention(
                                adjusted_start,
                                adjusted_end,
                                mention.text,
                                chunk.text,  # Use chunk text for better context
                                mention.mention_type
                            )
                    
                    # Merge with chunk characters
                    for name, char in sub_characters.items():
                        if name in chunk_characters:
                            existing = chunk_characters[name]
                            for mention in char.mentions:
                                if mention not in existing.mentions:
                                    existing.mentions.append(mention)
                            for variant in char.name_variants:
                                existing.add_variant(variant)
                        else:
                            chunk_characters[name] = char
                            
                except Exception as e:
                    print(f"Error in sub-chunk {j+1}: {e}")
            
            # Adjust positions to global text positions
            for char in chunk_characters.values():
                for mention in char.mentions:
                    adjusted_start = mention.start + chunk.start_pos
                    adjusted_end = mention.end + chunk.start_pos
                    char.mentions.remove(mention)
                    char.add_mention(
                        adjusted_start,
                        adjusted_end,
                        mention.text,
                        text,  # Use full text for better context
                        mention.mention_type
                    )
            
            # Merge with all characters
            for name, char in chunk_characters.items():
                if name in all_characters:
                    existing = all_characters[name]
                    for mention in char.mentions:
                        if mention not in existing.mentions:
                            existing.mentions.append(mention)
                    for variant in char.name_variants:
                        existing.add_variant(variant)
                    
                    # Update role and gender if not set
                    if not existing.role and char.role:
                        existing.role = char.role
                    if not existing.gender and char.gender:
                        existing.gender = char.gender
                else:
                    all_characters[name] = char
            
            # Log progress
            total_mentions = sum(len(c.mentions) for c in all_characters.values())
            print(f"Found {len(chunk_characters)} characters in chunk {i+1}")
            print(f"Total characters so far: {len(all_characters)}")
            print(f"Total mentions so far: {total_mentions}")
        
        return all_characters
        
    def _create_sub_chunks(self, text: str, max_tokens: int) -> List[str]:
        """Split text into sub-chunks that respect sentence boundaries."""
        tokens = self._count_tokens(text)
        if tokens <= max_tokens:
            return [text]
            
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_tokens = 0
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
            
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks
