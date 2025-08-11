"""Book Characters Module - Character analysis and extraction for gender transformation."""

# Import from unified analyzer (provides backward compatibility)
from .unified_analyzer import (
    UnifiedCharacterAnalyzer,
    ChunkingStrategy,
    analyze_book_characters,
    analyze_book_with_rate_limits
)

# Keep analyze_characters from old analyzer for now
from .analyzer import (
    analyze_characters,
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

# Legacy imports - will be removed in future
from .smart_chunked_analyzer import (
    analyze_book_characters_smart_chunks
)
from .rate_limited_analyzer import (
    RateLimitedAnalyzer
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
    'save_character_analysis',
    
    # Smart chunking
    'analyze_book_characters_smart_chunks',
    
    # Rate limiting
    'RateLimitedAnalyzer',
    'analyze_book_with_rate_limits'
]