# Changelog

All notable changes to the regender-xyz project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Multi-provider LLM support (OpenAI and Grok)
- Intelligent token-based chunking for optimal API usage
- Model-specific configuration system
- Automatic .env file loading
- Support for grok-3-mini-fast model
- Token estimation utilities
- Smart chunking that adapts to model context windows

### Changed
- Consolidated gender_transform_v2.py into gender_transform.py
- Updated json_transform.py to use smart chunking
- Improved analyze_characters.py to use unified API client
- Enhanced documentation with multi-provider information

### Removed
- Duplicate gender_transform_v2.py file
- Incomplete Moby Dick files (pg3201-*)
- Python cache files and system files

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