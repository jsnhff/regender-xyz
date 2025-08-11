"""Token counting and chunking utilities for optimal API usage."""

import re
from functools import lru_cache
from typing import List, Tuple, Optional, Dict, Any
from .model_configs import get_model_config

# Basic token estimation patterns
# These are approximations - actual tokenization varies by model
TOKEN_PATTERNS = {
    # Common contractions count as 1 token
    "contractions": r"\b(?:I'm|you're|he's|she's|it's|we're|they're|I've|you've|we've|they've|I'd|you'd|he'd|she'd|we'd|they'd|I'll|you'll|he'll|she'll|we'll|they'll|can't|won't|shouldn't|wouldn't|couldn't|didn't|doesn't|don't|isn't|aren't|wasn't|weren't|hasn't|haven't|hadn't)\b",
    
    # Punctuation that creates separate tokens
    "punctuation": r"[.!?,;:—–\-\"'()[\]{}]",
    
    # Numbers and special characters
    "numbers": r"\b\d+\b",
    "special": r"[@#$%^&*+=<>/\\|`~]"
}


@lru_cache(maxsize=1024)
def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    
    This is a rough approximation based on:
    - Average English word ≈ 1.3 tokens
    - Punctuation typically creates separate tokens
    - Whitespace doesn't count as tokens
    
    For exact counts, you'd need the actual tokenizer for each model.
    
    Note: This function is cached for performance. The same text will
    return the cached result on subsequent calls.
    """
    if not text:
        return 0
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Count words (split on whitespace and punctuation)
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)
    
    # Count punctuation marks
    punct_count = len(re.findall(TOKEN_PATTERNS["punctuation"], text))
    
    # Rough estimate: words * 1.3 + punctuation
    # This slightly overestimates to be safe
    estimated_tokens = int(word_count * 1.3 + punct_count)
    
    return estimated_tokens


def estimate_prompt_tokens(
    sentences: List[str],
    character_context: str,
    transform_type: str
) -> int:
    """Estimate total tokens for a transformation prompt."""
    
    # Base prompt template tokens (approximately)
    base_prompt_tokens = 150  # Instructions and formatting
    
    # Character context tokens
    context_tokens = estimate_tokens(character_context) if character_context else 0
    
    # Sentence tokens with [N] markers
    sentence_tokens = 0
    for i, sent in enumerate(sentences):
        # Add tokens for "[N] " marker
        marker_tokens = len(f"[{i}] ") // 2  # Rough estimate
        sentence_tokens += estimate_tokens(sent) + marker_tokens
    
    # Add some buffer for response formatting
    buffer_tokens = 50
    
    total = base_prompt_tokens + context_tokens + sentence_tokens + buffer_tokens
    return total


def calculate_safe_chunk_size(
    sentences: List[str],
    model_name: str,
    character_context: str = "",
    transform_type: str = "feminine"
) -> int:
    """
    Calculate safe chunk size based on model limits and content.
    
    Returns the number of sentences that can safely fit in one API call.
    """
    config = get_model_config(model_name)
    
    # Reserve tokens for output (transformation + response format)
    # We need roughly the same tokens for output as input
    available_input_tokens = config["context_window"] // 2
    
    # Further reduce to leave safety margin
    safe_input_tokens = int(available_input_tokens * 0.8)
    
    # Calculate fixed overhead
    overhead_tokens = estimate_prompt_tokens([], character_context, transform_type)
    
    # Available tokens for actual sentences
    available_for_sentences = safe_input_tokens - overhead_tokens
    
    if available_for_sentences <= 0:
        # Context is too large, need to reduce
        return 5  # Minimum chunk size
    
    # Binary search to find optimal chunk size
    left, right = 1, min(len(sentences), config["sentences_per_chunk"])
    optimal_size = left
    
    while left <= right:
        mid = (left + right) // 2
        chunk = sentences[:mid]
        
        # Estimate tokens for this chunk
        chunk_tokens = sum(estimate_tokens(sent) + len(f"[{i}] ") // 2 
                          for i, sent in enumerate(chunk))
        
        if chunk_tokens <= available_for_sentences:
            optimal_size = mid
            left = mid + 1
        else:
            right = mid - 1
    
    return max(optimal_size, 5)  # At least 5 sentences


def smart_chunk_sentences(
    sentences: List[str],
    model_name: str,
    character_context: str = "",
    transform_type: str = "feminine",
    verbose: bool = False
) -> List[List[str]]:
    """
    Intelligently chunk sentences based on token limits.
    
    Returns list of sentence chunks optimized for the model.
    """
    if not sentences:
        return []
    
    chunks = []
    remaining = sentences[:]
    config = get_model_config(model_name)
    
    while remaining:
        # Calculate optimal size for current chunk
        chunk_size = calculate_safe_chunk_size(
            remaining,
            model_name,
            character_context,
            transform_type
        )
        
        # Take the chunk
        chunk = remaining[:chunk_size]
        remaining = remaining[chunk_size:]
        
        if verbose:
            chunk_tokens = estimate_prompt_tokens(chunk, character_context, transform_type)
            print(f"      Chunk {len(chunks) + 1}: {len(chunk)} sentences, ~{chunk_tokens} tokens")
        
        chunks.append(chunk)
    
    return chunks


def analyze_book_for_chunking(
    book_data: Dict[str, Any],
    model_name: str
) -> Dict[str, Any]:
    """
    Analyze a book to predict chunking requirements for different models.
    """
    total_sentences = sum(len(ch['sentences']) for ch in book_data['chapters'])
    total_tokens = sum(
        estimate_tokens(' '.join(ch['sentences'])) 
        for ch in book_data['chapters']
    )
    
    # Analyze sentence length distribution
    all_sentences = []
    for chapter in book_data['chapters']:
        all_sentences.extend(chapter['sentences'])
    
    sentence_lengths = [len(sent.split()) for sent in all_sentences]
    avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    
    # Predict API calls for this model
    config = get_model_config(model_name)
    estimated_chunks = 0
    
    for chapter in book_data['chapters']:
        if chapter['sentences']:
            chunks = smart_chunk_sentences(
                chapter['sentences'],
                model_name,
                character_context="Sample context",
                verbose=False
            )
            estimated_chunks += len(chunks)
    
    return {
        "total_sentences": total_sentences,
        "total_tokens": total_tokens,
        "avg_sentence_length": avg_sentence_length,
        "model": model_name,
        "model_context_window": config["context_window"],
        "estimated_api_calls": estimated_chunks,
        "estimated_cost_factor": estimated_chunks * total_tokens / 1000  # Rough cost metric
    }