"""Smart chunking for optimal API usage."""

from typing import List, Optional
from .model_configs import calculate_optimal_chunk_size, get_model_config
from .token_utils import estimate_tokens


def smart_chunk_sentences(sentences: List[str], 
                         model: str,
                         character_context: str,
                         transform_type: str,
                         verbose: bool = False) -> List[List[str]]:
    """
    Intelligently chunk sentences based on token limits.
    
    Args:
        sentences: List of sentences to chunk
        model: Model name for token limits
        character_context: Character context string
        transform_type: Type of transformation
        verbose: Whether to print debug info
        
    Returns:
        List of sentence chunks
    """
    from .token_utils import smart_chunk_sentences as original_chunker
    return original_chunker(
        sentences, 
        model, 
        character_context,
        transform_type,
        verbose=verbose
    )