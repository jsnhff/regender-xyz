# Migration Guide: New Service-Oriented Architecture

## Overview

Phase 3 has introduced a new service-oriented architecture that provides:
- Clean separation of concerns
- Dependency injection
- Plugin system for providers
- Full async support
- Better testability

## Using the New Architecture

### Via CLI

The new architecture can be used through the CLI with a feature flag:

```bash
# Using the new architecture
python regender_cli_v2.py input.txt all_female --use-new-architecture

# Or set environment variable
export USE_NEW_ARCHITECTURE=true
python regender_cli_v2.py input.txt all_female
```

### Programmatically

```python
from src.app import Application

# Initialize application
app = Application("config/app.json")

# Process a book
result = app.process_book_sync(
    file_path="books/texts/pg1342.txt",
    transform_type="all_female",
    output_path="output.json",
    quality_control=True
)

# Clean up
app.shutdown()
```

## Architecture Components

### 1. Services

Services handle business logic and are managed by the dependency injection container:

- **ParserService**: Parses books from various formats
- **CharacterService**: Analyzes characters and genders
- **TransformService**: Applies gender transformations
- **QualityService**: Validates and improves quality

### 2. Domain Models

Clean domain models represent core business entities:

- **Book**: Complete book with chapters and metadata
- **Character**: Character with gender and attributes
- **Transformation**: Transformation results and changes

### 3. Strategies

Pluggable strategies for different algorithms:

- **ParsingStrategy**: Different parsing approaches
- **AnalysisStrategy**: Character analysis methods
- **TransformStrategy**: Transformation algorithms
- **QualityStrategy**: Quality control approaches

### 4. Providers

LLM providers as plugins:

- **OpenAIProvider**: OpenAI GPT models
- **AnthropicProvider**: Anthropic Claude models
- **UnifiedProvider**: Wrapper for existing api_client

### 5. Dependency Injection

Services are wired together automatically:

```python
from src.container import get_container

container = get_container()
container.register(
    'transform',
    TransformService,
    dependencies={
        'provider': 'llm_provider',
        'character_service': 'character'
    }
)
```

## Configuration

Configuration is now centralized in `config/app.json`:

```json
{
  "providers": [
    {
      "type": "unified",
      "module": "src.providers.unified_provider",
      "config": {}
    }
  ],
  "services": {
    "parser": {
      "class": "src.services.parser_service.ParserService",
      "config": {
        "cache_enabled": true
      }
    }
  }
}
```

## Testing

The new architecture is fully testable:

```python
import unittest
from src.services.base import BaseService

class TestService(unittest.TestCase):
    def test_service(self):
        service = MyService()
        result = service.process(data)
        self.assertEqual(result, expected)
```

## Migration Path

### Phase 1: Parallel Operation (Current)
- New architecture runs alongside old code
- Use feature flag to switch between them
- No breaking changes

### Phase 2: Gradual Migration
- Migrate one component at a time
- Update imports to use new modules
- Run parallel tests

### Phase 3: Full Migration
- Switch default to new architecture
- Deprecate old modules
- Clean up legacy code

## Benefits

### For Developers
- Cleaner code organization
- Easier to test and debug
- Better IDE support
- Simpler to add new features

### For Users
- Better performance (parallel processing)
- More reliable (retry logic)
- Higher quality output (improved QC)
- Easier configuration

## Backward Compatibility

The new architecture maintains full backward compatibility:

1. **Existing CLI still works**: Old commands continue to function
2. **APIs preserved**: Public interfaces remain the same
3. **File formats unchanged**: JSON/text formats are identical
4. **Configuration compatible**: Old configs still work

## Troubleshooting

### Issue: Import errors
**Solution**: Ensure `src/` is in Python path

### Issue: Provider not found
**Solution**: Check API keys are set in environment

### Issue: Service not registered
**Solution**: Verify service is in config/app.json

### Issue: Async errors
**Solution**: Use sync wrappers or run in async context

## Next Steps

1. Try the new architecture with `--use-new-architecture`
2. Review the new code in `src/`
3. Run tests with `python tests/test_new_architecture.py`
4. Provide feedback for improvements

## Support

For issues or questions:
- Check the documentation in `docs/`
- Review test examples in `tests/`
- Open an issue on GitHub