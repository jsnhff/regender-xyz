"""Model-specific configurations for optimal chunking."""

# Model context windows and recommended chunk sizes
MODEL_CONFIGS = {
    # OpenAI models
    "gpt-4": {
        "context_window": 8192,
        "output_limit": 4096,
        "sentences_per_chunk": 50,
        "max_chunk_tokens": 3000  # Conservative to leave room for prompt
    },
    "gpt-4o": {
        "context_window": 128000,
        "output_limit": 4096,
        "sentences_per_chunk": 100,
        "max_chunk_tokens": 6000
    },
    "gpt-4o-mini": {
        "context_window": 128000,
        "output_limit": 4096,
        "sentences_per_chunk": 75,
        "max_chunk_tokens": 4500
    },
    
    # Grok models
    "grok-beta": {
        "context_window": 131072,
        "output_limit": 8192,
        "sentences_per_chunk": 100,
        "max_chunk_tokens": 6000
    },
    "grok-3-mini-fast": {
        "context_window": 32768,  # Smaller context window
        "output_limit": 4096,
        "sentences_per_chunk": 30,  # Fewer sentences for mini model
        "max_chunk_tokens": 2500
    },
    "grok-3-latest": {
        "context_window": 131072,  # Large context window
        "output_limit": 131072,
        "sentences_per_chunk": 3600,  # Much larger chunks for efficiency
        "max_chunk_tokens": 98000
    },
    "grok-3-fast": {
        "context_window": 131072,
        "output_limit": 131072,
        "sentences_per_chunk": 500,  # Moderate chunks for faster processing
        "max_chunk_tokens": 30000
    },
    "grok-4-latest": {
        "context_window": 256000,  # Grok-4 has 256k context
        "output_limit": 131072,
        "sentences_per_chunk": 3600,  # Much larger chunks for efficiency
        "max_chunk_tokens": 98000
    },
    
    # Local models (MLX)
    "mistral-7b-instruct": {
        "context_window": 32768,      # Mistral-7B has 32K context
        "output_limit": 2048,
        "sentences_per_chunk": 50,    # Can handle more with larger context
        "max_chunk_tokens": 4000      # More aggressive chunking with 32K context
    },
    "mistral-7b-instruct-8bit": {
        "context_window": 32768,      # Same context window for 8bit version
        "output_limit": 2048,
        "sentences_per_chunk": 50,
        "max_chunk_tokens": 4000
    },
    
    # Default fallback
    "default": {
        "context_window": 8192,
        "output_limit": 4096,
        "sentences_per_chunk": 30,
        "max_chunk_tokens": 2500
    }
}


def get_model_config(model_name: str = None) -> dict:
    """Get configuration for a specific model."""
    if not model_name:
        return MODEL_CONFIGS["default"]
    
    # Try exact match first
    if model_name in MODEL_CONFIGS:
        return MODEL_CONFIGS[model_name]
    
    # Try partial match
    model_lower = model_name.lower()
    for key, config in MODEL_CONFIGS.items():
        if key.lower() in model_lower or model_lower in key.lower():
            return config
    
    # Fallback to default
    return MODEL_CONFIGS["default"]


def estimate_tokens(text: str) -> int:
    """Rough estimate of token count (1 token ≈ 4 characters)."""
    return len(text) // 4


def calculate_optimal_chunk_size(sentences: list, model_name: str = None) -> int:
    """Calculate optimal chunk size based on model and content."""
    config = get_model_config(model_name)
    max_sentences = config["sentences_per_chunk"]
    max_tokens = config["max_chunk_tokens"]
    
    # Start with model's recommended size
    chunk_size = max_sentences
    
    # Estimate average sentence length
    if sentences:
        avg_sentence_length = sum(len(s) for s in sentences[:10]) / min(10, len(sentences))
        estimated_tokens_per_sentence = estimate_tokens(str(avg_sentence_length))
        
        # Adjust if sentences are particularly long
        if estimated_tokens_per_sentence > 50:  # Long sentences
            chunk_size = min(chunk_size, max_tokens // estimated_tokens_per_sentence)
    
    return max(10, chunk_size)  # At least 10 sentences per chunk