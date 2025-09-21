# Character Deduplication Continuation Prompt

## Current State (2024-12-20)

We've implemented a rule-based character deduplication system, but it has significant limitations:

### Current Problems

1. **Hard-coded "common names" array** - Brittle and English-centric
2. **Rule-based matching** - Can't understand context (e.g., "Mary" could be multiple different characters)
3. **Post-processing approach** - Deduplicates after all chunks analyzed, losing context
4. **No semantic understanding** - Doesn't know that "The King" and "the duke" in Huck Finn are con artists' fake titles, not royalty

### The Better Approach: LLM-Powered Incremental Deduplication

## Proposed Architecture

```python
class SmartCharacterRegistry:
    """
    Maintains a growing set of unique characters using LLM for intelligent matching.
    Like a smart Set that uses AI to determine equality.
    """

    def __init__(self, llm_provider):
        self.characters = []  # List of confirmed unique characters
        self.llm = llm_provider

    async def add_or_merge(self, new_character: Character, context: str) -> Character:
        """
        Either adds a new character or merges with existing one.

        Args:
            new_character: Newly discovered character
            context: Text chunk where character was found

        Returns:
            The character entry (either new or existing with updated aliases)
        """
        if not self.characters:
            self.characters.append(new_character)
            return new_character

        # Use LLM to check against existing characters
        match = await self._find_match_with_llm(new_character, context)

        if match:
            # Merge into existing
            self._merge_into(match, new_character)
            return match
        else:
            # Add as new character
            self.characters.append(new_character)
            return new_character
```

## Key Design Decisions to Make

### 1. Incremental vs Batch Processing

**Current:** Process all chunks → Get all characters → Deduplicate at end

**Proposed:** Process chunk → Extract characters → Immediately check each against registry

**Benefits:**
- Context is fresh when making match decisions
- Can use surrounding text to disambiguate
- More memory efficient
- Can show progress in real-time

### 2. LLM Matching Strategy

Instead of rules, use LLM with context:

```python
async def _find_match_with_llm(self, new_char: Character, context: str) -> Optional[Character]:
    prompt = f"""
    I found a character "{new_char.name}" in this context:

    {context}

    Here are the characters I've already identified:
    {self._format_existing_characters()}

    Is "{new_char.name}" the same person as any existing character?
    Consider:
    - Nicknames and variations (Huck = Huckleberry Finn)
    - Titles that may vary (Mr./Mrs./Miss)
    - Context clues about their role
    - BUT be careful with common names - multiple people can be named Mary!

    Respond with JSON:
    {{
        "is_match": true/false,
        "matching_character": "name" or null,
        "confidence": 0.0-1.0,
        "reasoning": "brief explanation"
    }}
    """

    response = await self.llm.complete_async(prompt)
    # Parse and return match if found
```

### 3. Context Window Management

**Problem:** As we process more chunks, how much context do we keep?

**Options:**
1. Keep full text of where each character appeared (memory intensive)
2. Keep summary/key passages for each character
3. Keep only the aliases and descriptions, trust LLM's judgment

**Recommendation:** Hybrid approach
- Keep character's first appearance (usually most descriptive)
- Keep a running list of aliases/variations encountered
- For matching, provide:
  - New character's context (current chunk)
  - Existing character's first appearance
  - List of all variations seen

### 4. Handling Ambiguous Cases

Some names ARE ambiguous. The LLM should identify these:

```python
{
    "is_match": false,
    "matching_character": null,
    "confidence": 0.3,
    "reasoning": "While 'Mary' appears here, the context suggests this is Mary Jane Wilks (young woman, Peter Wilks' niece), not the same as the earlier Mary Williams (Huck's fake identity). Different people despite same first name."
}
```

### 5. Progressive Enhancement Strategy

**Phase 1: Single-chunk matching**
- When character found in chunk, immediately check against registry
- Use only current chunk as context

**Phase 2: Multi-chunk validation**
- After all chunks processed, do a validation pass
- "Are any of these actually the same person we missed?"
- Use broader context

**Phase 3: Relationship mapping**
- Use LLM to understand relationships
- "Jim" is "Miss Watson's Jim" - same person
- "The Duke" and "Bilgewater" - same con artist

## Implementation Plan

### Step 1: Refactor CharacterService

```python
class CharacterService:
    async def analyze_book_async(self, book: Book) -> CharacterAnalysis:
        registry = SmartCharacterRegistry(self.provider)

        for chunk in chunks:
            # Extract characters from this chunk
            chunk_characters = await self._analyze_chunk(chunk)

            # Add each to registry (with deduplication)
            for char in chunk_characters:
                await registry.add_or_merge(char, context=chunk)

        return CharacterAnalysis(characters=registry.get_all())
```

### Step 2: Optimize LLM Calls

Instead of checking each character individually:

```python
async def add_or_merge_batch(self, new_characters: List[Character], context: str):
    """Check multiple new characters at once."""

    prompt = f"""
    I found these characters in the text:
    {format_characters(new_characters)}

    Context where they appeared:
    {context}

    Here are characters I've already identified:
    {self._format_existing_characters()}

    For each new character, tell me if they match an existing one.
    """
```

### Step 3: Add Confidence Scoring

Track confidence in our deduplication:

```python
class Character:
    def __init__(self, ...):
        self.merge_confidence = 1.0  # How sure we are about merges
        self.merge_history = []  # Track what was merged
```

## Benefits of LLM-Based Approach

1. **Context-aware** - Understands "Mary Williams" is Huck in disguise, not a real woman
2. **Language agnostic** - Works for any language the LLM understands
3. **Adaptive** - Learns from the book's style and naming conventions
4. **Transparent** - LLM provides reasoning for each decision
5. **Correctable** - Can adjust confidence threshold or manually override

## Challenges to Address

1. **LLM Consistency** - Same question might get different answers
   - Solution: Use temperature=0, cache decisions

2. **Token Usage** - More LLM calls = more cost
   - Solution: Batch processing, smart caching

3. **Speed** - More API calls could slow analysis
   - Solution: Parallel processing, optimize prompts

4. **Complex Narratives** - Stories with disguises, time travel, etc.
   - Solution: Let LLM explain its reasoning, allow manual review

## Example: Huckleberry Finn

With LLM deduplication, we'd correctly identify:
- "Huck", "Huckleberry", "Huckleberry Finn" → Same person
- "Mary Williams", "Sarah Mary Williams", "George Peters" → All Huck in disguise
- "The King" and "the duke" → Two different con artists
- "Mary Jane Wilks" → Different from Mary Williams
- "Jim" and "Miss Watson's Jim" → Same person

## Next Session Tasks

1. **Remove hard-coded common names list**
2. **Implement SmartCharacterRegistry class**
3. **Create LLM-powered matching logic**
4. **Add incremental deduplication to chunk processing**
5. **Test on complex books with many characters**
6. **Add confidence scoring and reasoning tracking**
7. **Create UI/CLI for reviewing merge decisions**

## Questions for Next Session

1. Should we allow manual override of merge decisions?
2. How do we handle characters that are revealed to be the same person later in the book?
3. Should we track character name evolution throughout the story?
4. How do we handle unnamed characters ("the stranger", "a woman")?
5. Should we use different strategies for different genres?

---

*This approach transforms character deduplication from a brittle rule-based system to an intelligent, context-aware process that truly understands the narrative.*