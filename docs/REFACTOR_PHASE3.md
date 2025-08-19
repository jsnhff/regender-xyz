# Phase 3: Architecture Improvements (2 Weeks)

## Overview
Create a scalable, maintainable architecture with clear separation of concerns, dependency injection, and modern design patterns.

## Goals
- Implement service-oriented architecture
- Add dependency injection
- Create plugin system for extensibility
- Full async support
- Comprehensive error handling

## Prerequisites
- Phase 1 & 2 completed
- All tests passing
- Team alignment on architecture

## New Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   CLI Layer                          │
│              (regender_cli.py)                       │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│                Service Layer                         │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│   │ Parser   │ │Character │ │Transform │           │
│   │ Service  │ │ Service  │ │ Service  │           │
│   └──────────┘ └──────────┘ └──────────┘           │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│              Strategy Layer                          │
│   Chunking │ Analysis │ Transform │ Quality         │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│              Provider Layer                          │
│     OpenAI │ Anthropic │ Grok │ [Extensible]       │
└─────────────────────────────────────────────────────┘
```

## Week 1: Service Layer Implementation

### Day 1-2: Create Base Service Architecture

#### Task 3.1: Base Service Class
**New File**: `src/services/base.py`
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from dataclasses import dataclass

@dataclass
class ServiceConfig:
    """Configuration for services."""
    cache_enabled: bool = True
    async_enabled: bool = True
    max_retries: int = 3
    timeout: int = 300

class BaseService(ABC):
    """Base class for all services."""
    
    def __init__(self, config: Optional[ServiceConfig] = None):
        self.config = config or ServiceConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """Initialize service resources."""
        pass
    
    @abstractmethod
    async def process_async(self, data: Any) -> Any:
        """Async processing method."""
        pass
    
    def process(self, data: Any) -> Any:
        """Sync wrapper for async processing."""
        import asyncio
        return asyncio.run(self.process_async(data))
    
    def validate_input(self, data: Any) -> bool:
        """Validate input data."""
        return True
    
    def handle_error(self, error: Exception, context: Dict) -> None:
        """Centralized error handling."""
        self.logger.error(f"Error in {context}: {error}")
        raise
```

#### Task 3.2: Parser Service
**New File**: `src/services/parser_service.py`
```python
from typing import Dict, Optional, Union
from pathlib import Path
from src.services.base import BaseService
from src.models.book import Book, Chapter, Paragraph
from src.strategies.parsing import ParsingStrategy

class ParserService(BaseService):
    """Service for parsing books from various formats."""
    
    def __init__(self, strategy: Optional[ParsingStrategy] = None, **kwargs):
        super().__init__(**kwargs)
        self.strategy = strategy or self._get_default_strategy()
    
    def _initialize(self):
        """Initialize parser resources."""
        self.pattern_registry = PatternRegistry()
        self.validators = []
    
    async def process_async(self, input_path: Union[str, Path]) -> Book:
        """Parse a book from file."""
        input_path = Path(input_path)
        
        if not self.validate_input(input_path):
            raise ValueError(f"Invalid input: {input_path}")
        
        # Detect format
        format_type = await self._detect_format(input_path)
        
        # Parse using appropriate strategy
        raw_data = await self._read_file_async(input_path)
        parsed_data = await self.strategy.parse_async(raw_data, format_type)
        
        # Convert to domain model
        book = self._create_book_model(parsed_data)
        
        # Validate result
        self._validate_book(book)
        
        return book
    
    def _create_book_model(self, data: Dict) -> Book:
        """Convert parsed data to Book model."""
        chapters = []
        for chapter_data in data.get('chapters', []):
            paragraphs = [
                Paragraph(sentences=p['sentences'])
                for p in chapter_data.get('paragraphs', [])
            ]
            chapters.append(
                Chapter(
                    number=chapter_data.get('number'),
                    title=chapter_data.get('title'),
                    paragraphs=paragraphs
                )
            )
        
        return Book(
            title=data.get('metadata', {}).get('title'),
            author=data.get('metadata', {}).get('author'),
            chapters=chapters
        )
```

#### Task 3.3: Character Service
**New File**: `src/services/character_service.py`
```python
from typing import Dict, List, Optional
from src.services.base import BaseService
from src.models.book import Book
from src.models.character import Character, CharacterAnalysis
from src.strategies.analysis import AnalysisStrategy
from src.providers.base import LLMProvider

class CharacterService(BaseService):
    """Service for character analysis."""
    
    def __init__(self, 
                 provider: LLMProvider,
                 strategy: Optional[AnalysisStrategy] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.provider = provider
        self.strategy = strategy or self._get_default_strategy()
        self.cache = CharacterCache() if self.config.cache_enabled else None
    
    def _initialize(self):
        """Initialize character analysis resources."""
        self.prompt_generator = PromptGenerator()
        self.character_merger = CharacterMerger()
    
    async def process_async(self, book: Book) -> CharacterAnalysis:
        """Analyze characters in a book."""
        # Check cache
        if self.cache:
            cached = await self.cache.get_async(book.hash())
            if cached:
                return cached
        
        # Extract text for analysis
        text_chunks = await self.strategy.chunk_book_async(book)
        
        # Analyze each chunk
        chunk_results = await self._analyze_chunks_async(text_chunks)
        
        # Merge results
        characters = self.character_merger.merge(chunk_results)
        
        # Create analysis result
        analysis = CharacterAnalysis(
            book_id=book.hash(),
            characters=characters,
            metadata=self._generate_metadata(characters)
        )
        
        # Cache result
        if self.cache:
            await self.cache.set_async(book.hash(), analysis)
        
        return analysis
    
    async def _analyze_chunks_async(self, chunks: List[str]) -> List[Dict]:
        """Analyze text chunks in parallel."""
        import asyncio
        
        tasks = [
            self._analyze_single_chunk(chunk, idx)
            for idx, chunk in enumerate(chunks)
        ]
        
        # Limit concurrency
        semaphore = asyncio.Semaphore(self.config.max_concurrent or 5)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        return await asyncio.gather(*[limited_task(t) for t in tasks])
```

### Day 3-4: Transform and Quality Services

#### Task 3.4: Transform Service
**New File**: `src/services/transform_service.py`
```python
from typing import Optional
from src.services.base import BaseService
from src.models.book import Book
from src.models.transformation import Transformation, TransformType
from src.strategies.transform import TransformStrategy
from src.providers.base import LLMProvider

class TransformService(BaseService):
    """Service for gender transformation."""
    
    def __init__(self,
                 provider: LLMProvider,
                 character_service: CharacterService,
                 strategy: Optional[TransformStrategy] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.provider = provider
        self.character_service = character_service
        self.strategy = strategy or self._get_default_strategy()
    
    async def process_async(self, 
                          book: Book,
                          transform_type: TransformType) -> Transformation:
        """Transform a book's gender representation."""
        # Get character analysis
        characters = await self.character_service.process_async(book)
        
        # Create transformation context
        context = self._create_context(characters, transform_type)
        
        # Transform chapters in parallel
        transformed_chapters = await self._transform_chapters_async(
            book.chapters, context
        )
        
        # Create transformation result
        transformation = Transformation(
            original_book=book,
            transformed_chapters=transformed_chapters,
            transform_type=transform_type,
            characters_used=characters,
            metadata=self._generate_metadata()
        )
        
        return transformation
```

#### Task 3.5: Quality Service
**New File**: `src/services/quality_service.py`
```python
from src.services.base import BaseService
from src.models.transformation import Transformation
from src.strategies.quality import QualityStrategy

class QualityService(BaseService):
    """Service for quality control and validation."""
    
    def __init__(self,
                 strategy: Optional[QualityStrategy] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.strategy = strategy or AdaptiveQualityStrategy()
    
    async def process_async(self, transformation: Transformation) -> Transformation:
        """Improve transformation quality."""
        current_quality = await self._assess_quality(transformation)
        
        iterations = 0
        max_iterations = self.config.max_qc_iterations or 3
        
        while current_quality < self.config.target_quality and iterations < max_iterations:
            # Find issues
            issues = await self.strategy.find_issues_async(transformation)
            
            if not issues:
                break
            
            # Apply corrections
            transformation = await self._apply_corrections_async(
                transformation, issues
            )
            
            # Reassess
            current_quality = await self._assess_quality(transformation)
            iterations += 1
        
        transformation.quality_score = current_quality
        transformation.qc_iterations = iterations
        
        return transformation
```

### Day 5: Dependency Injection Container

#### Task 3.6: Service Container
**New File**: `src/container.py`
```python
from typing import Dict, Any, Type, Optional
from src.services.base import BaseService

class ServiceContainer:
    """Dependency injection container."""
    
    def __init__(self):
        self._services: Dict[str, BaseService] = {}
        self._factories: Dict[str, callable] = {}
        self._configs: Dict[str, Any] = {}
    
    def register(self, 
                 name: str,
                 service_class: Type[BaseService],
                 config: Optional[Dict] = None,
                 dependencies: Optional[Dict[str, str]] = None):
        """Register a service."""
        self._factories[name] = lambda: self._create_service(
            service_class, config, dependencies
        )
    
    def _create_service(self, 
                       service_class: Type[BaseService],
                       config: Optional[Dict],
                       dependencies: Optional[Dict[str, str]]):
        """Create service instance with dependencies."""
        # Resolve dependencies
        resolved_deps = {}
        if dependencies:
            for key, service_name in dependencies.items():
                resolved_deps[key] = self.get(service_name)
        
        # Create service
        return service_class(config=config, **resolved_deps)
    
    def get(self, name: str) -> BaseService:
        """Get or create a service."""
        if name not in self._services:
            if name not in self._factories:
                raise ValueError(f"Service {name} not registered")
            self._services[name] = self._factories[name]()
        return self._services[name]
    
    def configure(self, config_path: str):
        """Load configuration from file."""
        import json
        with open(config_path) as f:
            config = json.load(f)
        
        for service_name, service_config in config['services'].items():
            self.register(
                service_name,
                self._get_class(service_config['class']),
                service_config.get('config'),
                service_config.get('dependencies')
            )
```

## Week 2: Strategy Patterns and Plugins

### Day 1-2: Strategy Implementations

#### Task 3.7: Strategy Base Classes
**New File**: `src/strategies/base.py`
```python
from abc import ABC, abstractmethod
from typing import Any, List

class Strategy(ABC):
    """Base strategy interface."""
    
    @abstractmethod
    async def execute_async(self, data: Any) -> Any:
        """Execute strategy asynchronously."""
        pass

class ChunkingStrategy(Strategy):
    """Base class for chunking strategies."""
    
    @abstractmethod
    async def chunk_async(self, text: str, max_size: int) -> List[str]:
        """Chunk text into manageable pieces."""
        pass

class TransformStrategy(Strategy):
    """Base class for transformation strategies."""
    
    @abstractmethod
    async def transform_async(self, text: str, context: Dict) -> str:
        """Transform text according to strategy."""
        pass
```

#### Task 3.8: Plugin System
**New File**: `src/plugins/base.py`
```python
from abc import ABC, abstractmethod
from typing import Dict, Any
import importlib
import inspect

class Plugin(ABC):
    """Base plugin interface."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]):
        """Initialize plugin."""
        pass
    
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Any:
        """Execute plugin functionality."""
        pass

class PluginManager:
    """Manages plugin loading and execution."""
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
    
    def load_plugin(self, module_path: str):
        """Load a plugin from module."""
        module = importlib.import_module(module_path)
        
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, Plugin) and obj != Plugin:
                plugin = obj()
                self.register(plugin)
    
    def register(self, plugin: Plugin):
        """Register a plugin."""
        self.plugins[plugin.name] = plugin
        plugin.initialize({})
    
    def get(self, name: str) -> Plugin:
        """Get a plugin by name."""
        return self.plugins.get(name)
    
    def execute(self, name: str, context: Dict[str, Any]) -> Any:
        """Execute a plugin."""
        plugin = self.get(name)
        if not plugin:
            raise ValueError(f"Plugin {name} not found")
        return plugin.execute(context)
```

### Day 3-4: Provider Plugin System

#### Task 3.9: Provider Base and Plugins
**New File**: `src/providers/base.py`
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from src.plugins.base import Plugin

class LLMProvider(Plugin, ABC):
    """Base class for LLM provider plugins."""
    
    @abstractmethod
    async def complete_async(self,
                            messages: List[Dict[str, str]],
                            **kwargs) -> str:
        """Complete a prompt asynchronously."""
        pass
    
    @property
    def supports_json(self) -> bool:
        """Whether provider supports JSON mode."""
        return False
    
    @property
    def max_tokens(self) -> int:
        """Maximum token limit."""
        return 4096
    
    @property
    def rate_limit(self) -> Optional[int]:
        """Rate limit in requests per minute."""
        return None
```

**New File**: `src/providers/openai_provider.py`
```python
from src.providers.base import LLMProvider
import openai

class OpenAIProvider(LLMProvider):
    """OpenAI provider plugin."""
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def initialize(self, config: Dict[str, Any]):
        """Initialize OpenAI client."""
        self.client = openai.AsyncOpenAI(
            api_key=config.get('api_key'),
            base_url=config.get('base_url')
        )
        self.model = config.get('model', 'gpt-4o')
    
    async def complete_async(self, messages, **kwargs):
        """Complete using OpenAI API."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return response.choices[0].message.content
    
    @property
    def supports_json(self) -> bool:
        return True
    
    @property
    def max_tokens(self) -> int:
        return 128000
```

### Day 5: Configuration and Initialization

#### Task 3.10: Application Bootstrap
**New File**: `src/app.py`
```python
from src.container import ServiceContainer
from src.plugins.base import PluginManager
from pathlib import Path
import json

class Application:
    """Main application class."""
    
    def __init__(self, config_path: str = "config/app.json"):
        self.config = self._load_config(config_path)
        self.container = ServiceContainer()
        self.plugin_manager = PluginManager()
        self._initialize()
    
    def _load_config(self, path: str) -> Dict:
        """Load application configuration."""
        with open(path) as f:
            return json.load(f)
    
    def _initialize(self):
        """Initialize application components."""
        # Load provider plugins
        for provider in self.config.get('providers', []):
            self.plugin_manager.load_plugin(provider['module'])
        
        # Register services
        self.container.register(
            'parser',
            ParserService,
            self.config.get('parser_config')
        )
        
        self.container.register(
            'character',
            CharacterService,
            self.config.get('character_config'),
            dependencies={'provider': 'llm_provider'}
        )
        
        self.container.register(
            'transform',
            TransformService,
            self.config.get('transform_config'),
            dependencies={
                'provider': 'llm_provider',
                'character_service': 'character'
            }
        )
    
    def get_service(self, name: str):
        """Get a service from container."""
        return self.container.get(name)
    
    async def process_book(self, file_path: str, transform_type: str):
        """Process a book through the full pipeline."""
        # Parse
        parser = self.get_service('parser')
        book = await parser.process_async(file_path)
        
        # Transform
        transformer = self.get_service('transform')
        transformation = await transformer.process_async(book, transform_type)
        
        # Quality control
        qc = self.get_service('quality')
        transformation = await qc.process_async(transformation)
        
        return transformation
```

## Configuration Files

### app.json
```json
{
  "providers": [
    {
      "module": "src.providers.openai_provider",
      "config": {
        "api_key": "${OPENAI_API_KEY}",
        "model": "gpt-4o"
      }
    },
    {
      "module": "src.providers.anthropic_provider",
      "config": {
        "api_key": "${ANTHROPIC_API_KEY}",
        "model": "claude-opus-4"
      }
    }
  ],
  "services": {
    "parser": {
      "class": "src.services.parser_service.ParserService",
      "config": {
        "cache_enabled": true
      }
    },
    "character": {
      "class": "src.services.character_service.CharacterService",
      "config": {
        "cache_enabled": true,
        "max_concurrent": 5
      }
    }
  }
}
```

## Testing Phase 3

### Unit Tests
```python
# tests/test_services.py
async def test_parser_service():
    service = ParserService()
    book = await service.process_async("sample.txt")
    assert book.title is not None

async def test_service_container():
    container = ServiceContainer()
    container.register('test', TestService)
    service = container.get('test')
    assert isinstance(service, TestService)
```

### Integration Tests
```python
# tests/test_integration_phase3.py
async def test_full_pipeline():
    app = Application()
    result = await app.process_book(
        "books/texts/sample.txt",
        "all_female"
    )
    assert result.quality_score > 90
```

## Migration Path

### Gradual Migration
1. Keep old code working alongside new
2. Add feature flags for new architecture
3. Migrate one service at a time
4. Run parallel testing
5. Switch over when stable

### CLI Updates
```python
# regender_cli.py
def main():
    if USE_NEW_ARCHITECTURE:
        app = Application()
        asyncio.run(app.process_book(args.input, args.type))
    else:
        # Old code path
        legacy_process(args)
```

## Benefits After Phase 3

### Architectural Benefits
- **Clear separation of concerns**
- **Dependency injection**
- **Plugin system for extensibility**
- **Async throughout**
- **Testable components**

### Performance Benefits
- **Full parallelization**
- **Efficient resource usage**
- **Smart caching**
- **Optimized provider calls**

### Maintenance Benefits
- **Single responsibility principle**
- **Easy to add new providers**
- **Clear configuration**
- **Comprehensive logging**

## Next Steps

1. Review architecture with team
2. Set up new project structure
3. Implement base classes
4. Migrate services one by one
5. Add comprehensive tests
6. Document new architecture
7. Train team on new patterns