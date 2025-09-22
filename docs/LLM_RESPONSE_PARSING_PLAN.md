# LLM Response Parsing Refinement Plan

## Current State (September 21, 2025)

### The Problem

Our character analysis system is struggling with LLM response parsing, particularly when using Anthropic's Claude models. The issues include:

1. **Inconsistent JSON formatting** - LLMs sometimes return:
   - Valid JSON objects
   - JSON arrays instead of objects
   - JSON with markdown code blocks
   - Malformed JSON with missing commas or trailing commas
   - Truncated JSON responses
   - Plain text instead of JSON

2. **Current "Solutions" Are Brittle**:
   - Regex-based JSON fixing is error-prone
   - Multiple parsing strategies create complexity
   - No clear contract between what we request and what we receive

### Example Problem Outputs

```
WARNING - Invalid JSON response: Expecting ',' delimiter: line 21 column 28
WARNING - Could not parse JSON from response: [{"name": "Sally"...
WARNING - Failed to merge group: 'list' object has no attribute 'get'
```

## Root Cause Analysis

### 1. Prompt Engineering Issues
- We're asking for JSON but not being specific enough about the structure
- The prompt allows ambiguity (object vs array)
- No examples provided to the LLM

### 2. Provider-Specific Issues
- **Anthropic**: Doesn't have native JSON mode like OpenAI
- **OpenAI**: Has JSON mode but we're not using it properly
- Each provider needs different instructions for reliable JSON

### 3. Parsing Strategy Issues
- Trying to fix JSON after the fact instead of getting it right initially
- No validation of the JSON schema
- No type checking of the response structure

## Proposed Solution

### 1. Improve Prompt Engineering

#### For Character Extraction
```python
EXTRACTION_PROMPT = """
You are extracting character information from text.

Return a JSON object (NOT an array) with this EXACT structure:
{
  "characters": [
    {
      "name": "string - character's primary name",
      "gender": "string - male/female/unknown/neutral",
      "pronouns": "string - pronouns used",
      "description": "string - brief description",
      "aliases": ["array", "of", "alternate", "names"]
    }
  ]
}

IMPORTANT RULES:
1. Return ONLY valid JSON - no markdown, no explanation
2. Always return an object with a "characters" key, never a bare array
3. The "characters" value must be an array (can be empty)
4. Each character must have all fields (use empty strings/arrays if unknown)
5. Do not include any text before or after the JSON
"""
```

#### For Character Merging
```python
MERGE_PROMPT = """
Analyze if these characters are the same person.

Return a JSON object with this EXACT structure:
{
  "is_same_person": true/false,
  "canonical_name": "string - primary name to use",
  "gender": "string - male/female/unknown/neutral",
  "pronouns": "string",
  "description": "string - combined description",
  "aliases": ["array", "of", "alternate", "names"]
}

RULES:
1. Return ONLY valid JSON
2. All fields are required
3. Use empty strings/arrays rather than null
4. Do not explain your reasoning
"""
```

### 2. Provider-Specific Handling

```python
class ProviderJSONHandler:
    """Handle JSON responses appropriately for each provider."""

    @staticmethod
    def prepare_request(provider_type: str, messages: list, **kwargs) -> dict:
        """Prepare request with provider-specific JSON handling."""

        if provider_type == "openai":
            # Use OpenAI's JSON mode
            kwargs["response_format"] = {"type": "json_object"}
            # Add JSON instruction to last user message
            messages[-1]["content"] += "\n\nReturn valid JSON only."

        elif provider_type == "anthropic":
            # Add strong JSON instructions to system message
            system_msg = "You must respond with valid JSON only. No explanation, no markdown."
            if kwargs.get("system"):
                kwargs["system"] = kwargs["system"] + "\n\n" + system_msg
            else:
                kwargs["system"] = system_msg

        return kwargs
```

### 3. Response Validation with Pydantic

```python
from pydantic import BaseModel, ValidationError
from typing import List, Optional

class CharacterExtraction(BaseModel):
    """Schema for character extraction response."""
    name: str
    gender: str
    pronouns: str
    description: str
    aliases: List[str]

class CharacterExtractionResponse(BaseModel):
    """Schema for full extraction response."""
    characters: List[CharacterExtraction]

class CharacterMergeResponse(BaseModel):
    """Schema for character merge response."""
    is_same_person: bool
    canonical_name: str
    gender: str
    pronouns: str
    description: str
    aliases: List[str]

def parse_llm_response(response: str, schema: BaseModel) -> BaseModel:
    """Parse and validate LLM response against schema."""
    try:
        # Try to parse as JSON
        data = json.loads(response)

        # Validate against schema
        return schema(**data)

    except json.JSONDecodeError as e:
        # Log the actual response for debugging
        logger.error(f"Invalid JSON: {e}\nResponse: {response[:500]}")
        raise

    except ValidationError as e:
        # Schema validation failed
        logger.error(f"Schema validation failed: {e}")
        raise
```

### 4. Implement Retry with Better Prompts

```python
async def get_structured_response(
    provider: LLMProvider,
    prompt: str,
    schema: BaseModel,
    examples: Optional[List[dict]] = None,
    max_retries: int = 3
) -> BaseModel:
    """Get structured response from LLM with retries."""

    for attempt in range(max_retries):
        try:
            # Add examples if provided
            if examples and attempt > 0:
                prompt = add_examples_to_prompt(prompt, examples)

            # Add stronger JSON instructions on retry
            if attempt > 0:
                prompt = strengthen_json_instructions(prompt, attempt)

            response = await provider.complete(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3 if attempt > 0 else 0.5  # Lower temp on retry
            )

            # Parse and validate
            return parse_llm_response(response, schema)

        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == max_retries - 1:
                # Final attempt failed, use fallback
                logger.error(f"All attempts failed: {e}")
                return create_fallback_response(schema)

            # Log and retry
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(2 ** attempt)
```

### 5. Fallback Strategies

```python
def create_fallback_response(schema: BaseModel) -> BaseModel:
    """Create a minimal valid response when LLM fails."""

    if schema == CharacterExtractionResponse:
        return CharacterExtractionResponse(characters=[])

    elif schema == CharacterMergeResponse:
        return CharacterMergeResponse(
            is_same_person=False,
            canonical_name="Unknown",
            gender="unknown",
            pronouns="",
            description="",
            aliases=[]
        )
```

## Implementation Steps

### Phase 1: Create Response Schemas (Day 1)
1. Define Pydantic models for all LLM responses
2. Add validation rules and defaults
3. Create comprehensive test suite for schemas

### Phase 2: Improve Prompts (Day 1)
1. Rewrite all prompts with explicit JSON structure
2. Add examples to prompts
3. Create provider-specific prompt variants

### Phase 3: Implement Provider Handlers (Day 2)
1. Create ProviderJSONHandler class
2. Add provider detection and configuration
3. Test with both OpenAI and Anthropic

### Phase 4: Add Validation Layer (Day 2)
1. Integrate Pydantic validation
2. Implement retry logic with progressive prompting
3. Create fallback responses

### Phase 5: Remove Brittle Code (Day 3)
1. Remove regex-based JSON fixing
2. Remove multiple parsing strategies
3. Simplify error handling

## Success Metrics

1. **Parsing Success Rate**: >95% of LLM responses parse successfully
2. **No Regex Fixing**: Zero reliance on regex for JSON repair
3. **Clear Errors**: When parsing fails, error messages clearly indicate the issue
4. **Provider Parity**: Both OpenAI and Anthropic achieve similar success rates

## Example Usage

```python
class CharacterService:
    async def _extract_from_chunk(self, chunk: str, chunk_index: int) -> List[Dict]:
        """Extract characters with structured response handling."""

        prompt = self._build_extraction_prompt(chunk)

        response = await get_structured_response(
            provider=self.provider,
            prompt=prompt,
            schema=CharacterExtractionResponse,
            examples=EXTRACTION_EXAMPLES if chunk_index > 0 else None
        )

        # Convert Pydantic models to dicts
        return [char.dict() for char in response.characters]

    async def _merge_group_with_llm(self, group: List[Dict]) -> Character:
        """Merge character group with structured response."""

        prompt = self._build_merge_prompt(group)

        response = await get_structured_response(
            provider=self.provider,
            prompt=prompt,
            schema=CharacterMergeResponse
        )

        if response.is_same_person:
            return Character(
                name=response.canonical_name,
                gender=self._parse_gender(response.gender),
                pronouns=response.pronouns,
                aliases=response.aliases,
                description=response.description,
                importance="supporting",
                confidence=0.8
            )
        else:
            return self._dict_to_character(group[0])
```

## Testing Strategy

1. **Unit Tests**: Test each schema with valid/invalid data
2. **Integration Tests**: Test with real LLM responses from both providers
3. **Edge Cases**: Test with malformed JSON, truncated responses, arrays vs objects
4. **Performance**: Ensure parsing doesn't significantly impact response time

## Next Steps

1. Review and approve this plan
2. Create a new branch for implementation
3. Start with Phase 1 (schemas) as foundation
4. Iterate based on real-world results
5. Document patterns that work well for future reference

## Notes

The key insight is that we should enforce structure at the prompt and validation level, not try to fix broken responses after the fact. By being extremely explicit about what we want and validating it properly, we can eliminate most parsing issues.