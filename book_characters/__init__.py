"""Book Characters Module - Character analysis and extraction for gender transformation."""

from .analyzer import (
    analyze_characters,
    analyze_book_characters,
    get_full_text_from_json
)
# Scanner removed - using LLM only for character analysis
from .context import (
    create_character_context,
    create_all_female_mapping,
    create_character_mapping
)
from .loader import (
    load_character_file,
    validate_character_data
)
from .exporter import (
    export_characters_to_csv,
    export_character_graph,
    save_character_analysis
)

__all__ = [
    # Analyzer
    'analyze_characters',
    'analyze_book_characters',
    'get_full_text_from_json',
    
    # Scanner removed - using LLM only
    
    # Context
    'create_character_context',
    'create_all_female_mapping',
    'create_character_mapping',
    
    # Loader
    'load_character_file',
    'validate_character_data',
    
    # Exporter
    'export_characters_to_csv',
    'export_character_graph',
    'save_character_analysis'
]