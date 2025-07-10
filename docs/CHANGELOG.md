# Changelog

All notable changes to the regender-xyz project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2025-01-02

### Added
- Three explicit transformation modes: all_male, all_female, and gender_swap
- Quality control review loop system for ensuring 100% transformation accuracy
- Explicit character name mappings (Elizabeth→Elliot, Jane→John, etc.)
- Support for iterative learning passes in review loop
- Run_review_loop.py script for quality checking transformed texts
- New documentation: TRANSFORMATION_MODES.md explaining the three modes

### Changed
- **BREAKING**: Removed 'comprehensive' transformation type (use all_male/all_female/gender_swap instead)
- **BREAKING**: Removed 'masculine', 'feminine', 'neutral' transformation types
- Transformation prompts now use explicit, unambiguous instructions
- Review loop updated to support Grok provider
- Removed regex fallback in review loop (API-only approach)
- Updated all documentation to reflect new transformation modes

### Fixed
- Fixed issue where 'comprehensive' mode was hardcoded to map to 'feminine'
- Fixed gender mixing in transformations (now properly enforces single-gender outputs)
- Removed hardcoded gpt-4o-mini defaults throughout codebase
- Fixed model selection issues with Grok provider

### Refactored
- Simplified transformation type system to three clear modes
- Removed confusing transformation type mappings
- Cleaned up character context generation

## [0.8.0] - 2025-01-02

### Added
- Pure LLM-based character analysis (removed regex scanning for better accuracy)
- Smart chunking strategy for comprehensive book coverage with Grok
- Support for Grok-3-latest model with 131k context window
- Pre-analyzed character support for faster processing
- Numbered sentence transformation approach for perfect alignment
- Handles 100+ characters per book (tested on Harry Potter)
- Strategic chunk analysis (beginning, middle, end sections)
- Character position tracking (where characters first appear)
- Anti-merging rules to prevent family member confusion

### Changed
- Character analysis now uses LLM exclusively for better accuracy
- Improved sentence boundary detection for abbreviations (Mr., Mrs., Dr., etc.)
- Enhanced name transformations (e.g., Harry → Harriet)
- Better handling of complex family relationships
- Optimized context usage for Grok (85% vs 70% for others)
- Updated prompts to prevent character merging issues

### Fixed
- Fixed character consolidation bug where family members were merged
- Resolved sentence splitting issues around abbreviations
- Fixed Grok API key conflicts with environment variables
- Corrected Grok model selection (grok-3-latest vs grok-beta)
- Fixed JSON output formatting for Grok provider

### Performance
- Character analysis: 5-10 minutes for 400k character books with Grok
- Found 106 characters in Harry Potter (vs 70-95 with other methods)
- Reduced API calls through smart chunking strategy

## [0.7.0] - 2024-01-20

### Added
- Full paragraph preservation in JSON structure for accurate text recreation
- Intelligent abbreviation handling (Mr., Mrs., Dr., etc.) in sentence splitting
- Comprehensive MLX support with improved JSON parsing for local models
- Robust error handling for character analysis failures
- Fallback mechanisms for MLX JSON generation issues
- Backward compatibility for both old (flat sentences) and new (paragraphs) JSON structures

### Changed
- Main CLI is now `regender_book_cli.py` (consolidated functionality)
- Renamed `gender_transform` module to `book_transform` for clarity
- Improved sentence splitting to handle abbreviations correctly
- Enhanced JSON structure to preserve paragraph breaks
- Updated transform system to maintain paragraph structure
- Reorganized project with unified `books/` directory structure
- Made internal API client classes private (prefixed with underscore)

### Removed
- Obsolete CLI files: `regender_cli.py`, `cli_visuals.py`, `interactive_cli.py`
- Temporary utility: `process_new_texts.py`
- Redundant `utils.py` (moved essential functions to `book_transform/utils.py`)
- Duplicate `safe_api_call` decorator from `api_client.py`
- Verse detection complexity (simplified to paragraph-only structure)

### Fixed
- Character analysis now gracefully handles MLX JSON parsing errors
- MLX transformations continue even if character analysis fails
- Improved JSON extraction from MLX model responses

## [0.5.0] - 2024-01-15

### Added
- Modular book parser with 100% success rate on Gutenberg collection
- Pattern registry system with priority-based matching
- Support for 100+ book formats including international languages
- Smart section detection with fallback strategies
- Gutenberg CLI for easy book downloading and processing

### Changed
- Complete parser overhaul from monolithic to modular architecture
- Improved chapter detection accuracy from 72% to 100%
- Enhanced pattern matching with language-specific support

## [0.4.0] - 2024-01-10

### Added
- Book preprocessing pipeline
- JSON-based transformation workflow
- Character analysis module
- CLI commands for full pipeline processing

### Changed
- Improved sentence splitting algorithm
- Enhanced artifact removal
- Better dialogue handling

## [0.3.0] - 2024-01-05

### Added
- Basic gender transformation functionality
- Support for feminine, masculine, and neutral transformations
- OpenAI API integration
- Simple CLI interface

### Changed
- Improved text processing accuracy
- Enhanced error handling

## [0.2.0] - 2024-01-01

### Added
- Initial book parser
- Basic chapter detection
- Text cleaning utilities

## [0.1.0] - 2023-12-28

### Added
- Initial project structure
- Basic CLI framework
- Project documentation