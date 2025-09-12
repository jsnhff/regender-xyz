# Technical Implementation Details

## Core Technologies

### Language & Runtime
- **Python 3.9+**: Modern Python with type hints
- **Async/Await**: Asynchronous processing for concurrency
- **Dataclasses**: Clean data model definitions
- **ABC (Abstract Base Classes)**: Interface definitions

### Dependencies
```python
# Core Libraries
asyncio          # Asynchronous programming
logging          # Structured logging
json             # Data serialization
pathlib          # Path manipulation
hashlib          # Content hashing

# External Dependencies
openai           # OpenAI API client
anthropic        # Anthropic/Claude API
requests         # HTTP client (legacy)
```

## Service Implementation Details

### 1. Parser Service Architecture

#### Text Processing Pipeline
```python
Raw Text
    ↓
Format Detection (DetectorParser)
    ↓
Specialized Parser Selection
    ├── GutenbergParser (Project Gutenberg)
    ├── PlayParser (Theatrical scripts)
    └── StandardParser (General text)
    ↓
Hierarchy Extraction
    ├── Chapter Detection
    ├── Section Identification
    └── Paragraph Segmentation
    ↓
Sentence Tokenization
    ↓
JSON Serialization
```

#### Pattern Recognition System
- **Chapter Patterns**: 30+ regex patterns for different formats
- **Priority System**: Weighted pattern matching
- **Abbreviation Handling**: 100+ common abbreviations
- **Language Support**: English, French, German, Spanish

### 2. Character Service Implementation

#### Analysis Pipeline
```python
class CharacterService:
    async def analyze_book(book: Book):
        # 1. Smart chunking
        chunks = self._create_smart_chunks(book)
        
        # 2. Parallel analysis with rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = [analyze_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks)
        
        # 3. Merge and deduplicate
        characters = self._merge_characters(results)
        
        # 4. Validate and score
        return self._validate_characters(characters)
```

#### LLM Prompt Engineering
```python
CHARACTER_ANALYSIS_PROMPT = """
Analyze this text and identify all characters mentioned.
For each character, determine:
1. Full name and any aliases
2. Gender (male/female/nonbinary/unknown)
3. Pronouns used in text
4. Titles (Mr., Mrs., Dr., etc.)
5. Importance (main/supporting/minor)

Return as JSON with confidence scores.
"""
```

### 3. Transform Service Architecture

#### Transformation Strategies
```python
def transform_text(text, characters, transform_type):
    if transform_type == "gender_swap":
        return swap_genders(text, characters)
    elif transform_type == "all_female":
        return make_all_female(text, characters)
    elif transform_type == "all_male":
        return make_all_male(text, characters)
    elif transform_type == "nonbinary":
        return make_nonbinary(text, characters)
```

#### Context-Aware Replacement
```python
class ContextAwareReplacer:
    def replace(self, text, character, new_pronouns):
        # Build replacement map
        replacements = {
            character.pronouns['subject']: new_pronouns['subject'],
            character.pronouns['object']: new_pronouns['object'],
            character.pronouns['possessive']: new_pronouns['possessive']
        }
        
        # Apply with case preservation
        for old, new in replacements.items():
            text = self._replace_preserving_case(text, old, new)
        
        return text
```

### 4. Quality Service Implementation

#### Quality Scoring Algorithm
```python
def calculate_quality_score(original, transformed, characters):
    scores = []
    
    # Check pronoun consistency
    pronoun_score = check_pronoun_consistency(transformed, characters)
    scores.append(pronoun_score * 0.4)
    
    # Check name consistency
    name_score = check_name_consistency(transformed, characters)
    scores.append(name_score * 0.3)
    
    # Check completeness
    completeness = check_transformation_completeness(original, transformed)
    scores.append(completeness * 0.3)
    
    return sum(scores)
```

#### Iterative Improvement
```python
async def improve_quality(text, target_score=90):
    current_score = 0
    iterations = 0
    
    while current_score < target_score and iterations < MAX_ITERATIONS:
        # Identify issues
        issues = identify_quality_issues(text)
        
        # Generate fixes
        fixes = await generate_fixes(issues)
        
        # Apply fixes
        text = apply_fixes(text, fixes)
        
        # Recalculate score
        current_score = calculate_quality_score(text)
        iterations += 1
    
    return text, current_score
```

## Provider Integration Details

### Unified Client Implementation
```python
class UnifiedLLMClient:
    def __init__(self, provider=None):
        self.providers = {
            "openai": OpenAIClient(),
            "anthropic": AnthropicClient()
        }
        self.provider = self._select_provider(provider)
    
    async def complete(self, messages, **kwargs):
        # Provider-specific handling
        if self.provider == "openai":
            return await self._openai_complete(messages, **kwargs)
        elif self.provider == "anthropic":
            return await self._anthropic_complete(messages, **kwargs)
```

### Rate Limiting & Retry Logic
```python
class RateLimiter:
    def __init__(self, requests_per_minute):
        self.rpm = requests_per_minute
        self.last_request = 0
        
    async def acquire(self):
        now = time.time()
        time_since_last = now - self.last_request
        min_interval = 60.0 / self.rpm
        
        if time_since_last < min_interval:
            await asyncio.sleep(min_interval - time_since_last)
        
        self.last_request = time.time()

@retry(max_attempts=3, backoff=exponential)
async def api_call_with_retry(client, messages):
    try:
        return await client.complete(messages)
    except APIError as e:
        if e.is_retryable():
            raise  # Will trigger retry
        return None
```

## Data Structures

### Book JSON Schema
```json
{
  "title": "string",
  "author": "string",
  "metadata": {
    "source": "string",
    "language": "string",
    "publication_date": "string"
  },
  "chapters": [
    {
      "number": "integer",
      "title": "string",
      "paragraphs": [
        {
          "sentences": ["string"]
        }
      ]
    }
  ],
  "characters": [
    {
      "name": "string",
      "gender": "enum",
      "pronouns": {
        "subject": "string",
        "object": "string",
        "possessive": "string"
      },
      "aliases": ["string"],
      "importance": "enum"
    }
  ]
}
```

### Transformation Result Schema
```json
{
  "success": "boolean",
  "book_title": "string",
  "transformation_type": "string",
  "quality_score": "float",
  "iterations": "integer",
  "processing_time": "float",
  "provider": "string",
  "model": "string",
  "chapters_processed": "integer",
  "characters_transformed": "integer",
  "output_path": "string"
}
```

## Performance Optimizations

### 1. Smart Chunking Algorithm
```python
def create_smart_chunks(text, max_tokens=4000):
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for paragraph in text.paragraphs:
        paragraph_tokens = estimate_tokens(paragraph)
        
        if current_tokens + paragraph_tokens > max_tokens:
            # Start new chunk
            chunks.append(current_chunk)
            current_chunk = [paragraph]
            current_tokens = paragraph_tokens
        else:
            current_chunk.append(paragraph)
            current_tokens += paragraph_tokens
    
    return chunks
```

### 2. Parallel Processing
```python
async def process_chapters_parallel(chapters, max_concurrent=5):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_limit(chapter):
        async with semaphore:
            return await process_chapter(chapter)
    
    tasks = [process_with_limit(ch) for ch in chapters]
    return await asyncio.gather(*tasks)
```

### 3. Caching Strategy
```python
class CachedService:
    def __init__(self):
        self.cache = {}
        
    def get_cache_key(self, *args):
        return hashlib.md5(str(args).encode()).hexdigest()
    
    async def process(self, data):
        cache_key = self.get_cache_key(data)
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        result = await self._process_impl(data)
        self.cache[cache_key] = result
        return result
```

## Error Handling

### Exception Hierarchy
```python
class RegenderError(Exception):
    """Base exception for all regender errors"""

class ParsingError(RegenderError):
    """Error during text parsing"""

class APIError(RegenderError):
    """Error calling LLM API"""

class TransformationError(RegenderError):
    """Error during transformation"""

class QualityError(RegenderError):
    """Quality threshold not met"""
```

### Error Recovery
```python
async def safe_process(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except APIError as e:
        if e.is_rate_limit():
            await asyncio.sleep(60)
            return await safe_process(func, *args, **kwargs)
        elif e.is_timeout():
            # Retry with smaller chunk
            return await process_with_smaller_chunks(*args, **kwargs)
        else:
            raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return create_error_result(e)
```

## Testing Strategies

### Unit Test Pattern
```python
class TestCharacterService(unittest.TestCase):
    def setUp(self):
        self.service = CharacterService()
        self.mock_provider = Mock()
        
    async def test_character_detection(self):
        # Arrange
        text = "Elizabeth Bennet met Mr. Darcy."
        expected = [
            Character(name="Elizabeth Bennet", gender=Gender.FEMALE),
            Character(name="Mr. Darcy", gender=Gender.MALE)
        ]
        
        # Act
        result = await self.service.analyze_text(text)
        
        # Assert
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "Elizabeth Bennet")
```

### Integration Test Pattern
```python
async def test_end_to_end_transformation():
    # Load test book
    book_path = "test_data/sample_book.txt"
    
    # Run complete pipeline
    app = Application()
    result = await app.process_book(
        book_path,
        transform_type="gender_swap",
        quality_control=True
    )
    
    # Validate results
    assert result['success']
    assert result['quality_score'] >= 90
    assert 'output_path' in result
```

## Logging & Monitoring

### Structured Logging
```python
import logging
import json

class StructuredLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        
    def log_event(self, event, **kwargs):
        log_data = {
            'event': event,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        self.logger.info(json.dumps(log_data))

# Usage
logger.log_event('transformation_complete', 
                 book='Pride and Prejudice',
                 duration=125.3,
                 quality_score=92.5)
```

### Performance Metrics
```python
class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(list)
    
    @contextmanager
    def timer(self, operation):
        start = time.time()
        yield
        duration = time.time() - start
        self.metrics[operation].append(duration)
    
    def get_stats(self, operation):
        times = self.metrics[operation]
        return {
            'count': len(times),
            'mean': np.mean(times),
            'p50': np.percentile(times, 50),
            'p95': np.percentile(times, 95),
            'p99': np.percentile(times, 99)
        }
```

## Security Considerations

### API Key Management
```python
class SecureConfig:
    @staticmethod
    def get_api_key(provider):
        # Never hardcode keys
        key = os.environ.get(f'{provider.upper()}_API_KEY')
        
        if not key:
            # Try loading from secure file
            key = load_from_secure_store(provider)
        
        if not key:
            raise ConfigError(f"No API key found for {provider}")
        
        return key
```

### Input Validation
```python
def validate_input(file_path):
    # Check file exists
    if not os.path.exists(file_path):
        raise ValueError(f"File not found: {file_path}")
    
    # Check file size
    max_size = 10 * 1024 * 1024  # 10MB
    if os.path.getsize(file_path) > max_size:
        raise ValueError(f"File too large: {file_path}")
    
    # Check file type
    if not file_path.endswith(('.txt', '.json')):
        raise ValueError(f"Unsupported file type: {file_path}")
```

## Deployment Considerations

### Docker Configuration
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "regender_cli.py"]
```

### Environment Setup
```bash
# .env.production
DEFAULT_PROVIDER=openai
DEFAULT_MODEL=gpt-4o
LOG_LEVEL=INFO
MAX_CONCURRENT=10
CACHE_ENABLED=true
QUALITY_TARGET=90
```

This technical documentation provides a comprehensive view of the implementation details, algorithms, and architectural decisions in the Regender-XYZ system.