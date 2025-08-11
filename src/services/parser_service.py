"""
Parser Service

This service handles parsing books from various text formats into
the structured Book domain model.
"""

from typing import Dict, Optional, Union, List, Any
from pathlib import Path
import json
import asyncio

from src.services.base import BaseService, ServiceConfig
from src.models.book import Book, Chapter, Paragraph
from src.strategies.parsing import ParsingStrategy, StandardParsingStrategy


class ParserService(BaseService):
    """
    Service for parsing books from various formats.
    
    This service:
    - Detects book format (standard, play, multi-part, etc.)
    - Parses text into structured format
    - Validates the result
    - Converts to domain model
    """
    
    def __init__(self, 
                 strategy: Optional[ParsingStrategy] = None,
                 config: Optional[ServiceConfig] = None):
        """
        Initialize parser service.
        
        Args:
            strategy: Parsing strategy to use
            config: Service configuration
        """
        self.strategy = strategy or self._get_default_strategy()
        super().__init__(config)
    
    def _initialize(self):
        """Initialize parser resources."""
        self.validators = []
        self.format_cache = {}
        
        # Set up logging
        self.logger.info(f"Initialized {self.__class__.__name__}")
    
    def _get_default_strategy(self) -> ParsingStrategy:
        """Get the default parsing strategy."""
        return StandardParsingStrategy()
    
    async def process_async(self, input_path: Union[str, Path]) -> Book:
        """
        Parse a book from file.
        
        Args:
            input_path: Path to the input file
            
        Returns:
            Parsed Book object
            
        Raises:
            ValueError: If input is invalid
            IOError: If file cannot be read
        """
        input_path = Path(input_path)
        
        # Validate input
        if not self.validate_input(input_path):
            raise ValueError(f"Invalid input: {input_path}")
        
        try:
            # Read file
            raw_data = await self._read_file_async(input_path)
            
            # Detect format
            format_type = await self._detect_format(raw_data)
            self.logger.info(f"Detected format: {format_type}")
            
            # Parse using strategy
            parsed_data = await self.strategy.parse_async(raw_data, format_type)
            
            # Convert to domain model
            book = self._create_book_model(parsed_data)
            book.source_file = str(input_path)
            
            # Validate result
            errors = self._validate_book(book)
            if errors:
                self.logger.warning(f"Validation warnings: {errors}")
            
            return book
            
        except Exception as e:
            self.handle_error(e, {"input_path": str(input_path)})
    
    async def parse_json_async(self, json_path: Union[str, Path]) -> Book:
        """
        Load a book from JSON file.
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Book object
        """
        json_path = Path(json_path)
        
        async with asyncio.Lock():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        return Book.from_dict(data)
    
    def validate_input(self, input_path: Path) -> bool:
        """
        Validate input file.
        
        Args:
            input_path: Path to validate
            
        Returns:
            True if valid
        """
        if not input_path.exists():
            self.logger.error(f"File not found: {input_path}")
            return False
        
        if not input_path.is_file():
            self.logger.error(f"Not a file: {input_path}")
            return False
        
        # Check file size (max 50MB)
        max_size = 50 * 1024 * 1024
        if input_path.stat().st_size > max_size:
            self.logger.error(f"File too large: {input_path}")
            return False
        
        return True
    
    async def _read_file_async(self, file_path: Path) -> str:
        """
        Read file asynchronously.
        
        Args:
            file_path: Path to file
            
        Returns:
            File contents
        """
        loop = asyncio.get_event_loop()
        
        def read_file():
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        return await loop.run_in_executor(None, read_file)
    
    async def _detect_format(self, text: str) -> str:
        """
        Detect text format.
        
        Args:
            text: Text to analyze
            
        Returns:
            Format identifier
        """
        # Check cache
        text_hash = hash(text[:1000])  # Hash first 1000 chars
        if text_hash in self.format_cache:
            return self.format_cache[text_hash]
        
        # Detect format
        format_type = await self.strategy.detect_format_async(text)
        
        # Cache result
        self.format_cache[text_hash] = format_type
        
        return format_type
    
    def _create_book_model(self, data: Dict) -> Book:
        """
        Convert parsed data to Book model.
        
        Args:
            data: Parsed book data
            
        Returns:
            Book object
        """
        chapters = []
        
        for i, chapter_data in enumerate(data.get('chapters', [])):
            # Create paragraphs
            paragraphs = []
            for para_data in chapter_data.get('paragraphs', []):
                if isinstance(para_data, dict):
                    sentences = para_data.get('sentences', [])
                elif isinstance(para_data, str):
                    sentences = [para_data]
                else:
                    sentences = []
                
                if sentences:
                    paragraphs.append(Paragraph(sentences=sentences))
            
            # Create chapter
            chapter = Chapter(
                number=chapter_data.get('number', i + 1),
                title=chapter_data.get('title'),
                paragraphs=paragraphs,
                metadata=chapter_data.get('metadata', {})
            )
            chapters.append(chapter)
        
        # Extract metadata
        metadata = data.get('metadata', {})
        
        return Book(
            title=metadata.get('title'),
            author=metadata.get('author'),
            chapters=chapters,
            metadata={
                k: v for k, v in metadata.items() 
                if k not in ['title', 'author']
            }
        )
    
    def _validate_book(self, book: Book) -> List[str]:
        """
        Validate book structure.
        
        Args:
            book: Book to validate
            
        Returns:
            List of validation errors
        """
        errors = book.validate()
        
        # Additional service-specific validation
        if book.word_count() < 100:
            errors.append("Book appears too short (< 100 words)")
        
        if book.chapter_count() > 500:
            errors.append("Unusually high chapter count (> 500)")
        
        return errors
    
    async def save_as_json_async(self, book: Book, output_path: Union[str, Path]) -> None:
        """
        Save book as JSON.
        
        Args:
            book: Book to save
            output_path: Output file path
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = book.to_dict()
        
        loop = asyncio.get_event_loop()
        
        def save_json():
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        await loop.run_in_executor(None, save_json)
        self.logger.info(f"Saved book to {output_path}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        metrics = super().get_metrics()
        metrics.update({
            "strategy": self.strategy.__class__.__name__,
            "format_cache_size": len(self.format_cache)
        })
        return metrics