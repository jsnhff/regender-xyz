"""
Book transformation package.

This package handles AI-based transformation of parsed books,
including gender swapping and other narrative modifications.
"""

from .transform import BookTransformer, transform_book
# Character analysis moved to book_characters module
from .llm_transform import transform_text_with_llm, transform_gender_with_context, TRANSFORM_TYPES
from .quality_control import quality_control_loop, validate_transformation
from .unified_transform import UnifiedBookTransformer, transform_book_unified

# Simple file transformation wrapper
def transform_text_file(file_path: str, transform_type: str, output_path: str = None, model: str = "gpt-4o-mini", **kwargs):
    """Transform a text file with the specified transformation type."""
    from pathlib import Path
    
    # Read the input file
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Transform the text
    transformed_text = transform_text_with_llm(text, transform_type, model=model)
    
    # Save to output file if specified
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(transformed_text)
    
    return transformed_text


__version__ = "1.0.0"
__all__ = [
    "BookTransformer",
    "transform_book",
    "transform_text_with_llm",
    "transform_gender_with_context",
    "transform_text_file",
    "TRANSFORM_TYPES",
    "quality_control_loop",
    "validate_transformation",
    "UnifiedBookTransformer",
    "transform_book_unified"
]