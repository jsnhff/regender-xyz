#!/usr/bin/env python3
"""
Test integration design for character-based transformation in CLI.

This demonstrates how to cleanly integrate the character-based transformation
approach into the existing CLI without disrupting the current functionality.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any

def proposed_cli_usage():
    """
    Proposed CLI usage examples for character-based transformation.
    
    Option 1: Use pre-analyzed character file
    python regender_book_cli.py transform book.json \
        --characters book_characters.json \
        --type comprehensive
    
    Option 2: Analyze and save characters for reuse
    python regender_book_cli.py analyze-characters book.json \
        --output book_characters.json
    
    Option 3: Transform with custom character mappings
    python regender_book_cli.py transform book.json \
        --characters custom_characters.json \
        --type comprehensive
    """
    pass


def transform_with_characters_wrapper(
    book_data: Dict[str, Any],
    character_file: Optional[str] = None,
    transform_type: str = 'comprehensive',
    model: str = 'gpt-4o-mini',
    provider: Optional[str] = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Wrapper function to integrate character-based transformation.
    
    This would be added to book_transform module as an enhancement.
    """
    from book_transform import transform_book
    import book_transform.character_analyzer as char_analyzer
    
    if character_file and Path(character_file).exists():
        # Load pre-analyzed characters
        with open(character_file, 'r') as f:
            character_data = json.load(f)
        
        # Extract characters (handle different formats)
        if 'characters' in character_data:
            characters = character_data['characters']
        else:
            characters = character_data
        
        # Create context
        context = char_analyzer.create_character_context(characters)
        
        # Temporarily override the analyzer
        original_analyze = char_analyzer.analyze_book_characters
        
        def mock_analyze(book_data, model=None, provider=None, sample_size=None, verbose=True):
            if verbose:
                print(f"✅ Using pre-analyzed characters from: {character_file}")
                print(f"  Loaded {len(characters)} characters")
            return characters, context
        
        char_analyzer.analyze_book_characters = mock_analyze
        
        try:
            # Run transformation
            result = transform_book(
                book_data,
                transform_type=transform_type,
                model=model,
                provider=provider,
                verbose=verbose
            )
            
            # Add metadata about character source
            result['metadata']['character_source'] = character_file
            result['metadata']['character_analysis'] = 'pre-loaded'
            
            return result
            
        finally:
            # Restore original
            char_analyzer.analyze_book_characters = original_analyze
    else:
        # Standard transformation (auto-detect characters)
        return transform_book(
            book_data,
            transform_type=transform_type,
            model=model,
            provider=provider,
            verbose=verbose
        )


def analyze_characters_command(
    input_file: str,
    output_file: str,
    model: str = 'gpt-4o-mini',
    provider: Optional[str] = None
):
    """
    New command to analyze and save characters for reuse.
    
    This would be added as a new CLI command.
    """
    from book_transform.character_analyzer import analyze_book_characters
    from book_parser import load_book_json
    
    print(f"📖 Analyzing characters in: {input_file}")
    
    # Load book
    book_data = load_book_json(input_file)
    
    # Analyze characters
    characters, context = analyze_book_characters(
        book_data,
        model=model,
        provider=provider,
        verbose=True
    )
    
    # Save to file
    output_data = {
        'metadata': {
            'source_book': input_file,
            'analysis_model': model,
            'analysis_provider': provider,
            'character_count': len(characters)
        },
        'characters': characters,
        'context': context
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✅ Saved character analysis to: {output_file}")
    print(f"📊 Total characters: {len(characters)}")


def create_custom_character_mapping(
    character_file: str,
    target_gender: str = 'female',
    specific_mappings: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Create custom character mappings for transformation.
    
    Example:
    specific_mappings = {
        'Harry Potter': {'name': 'Harriet Potter', 'gender': 'female'},
        'Ron Weasley': {'name': 'Veronica Weasley', 'gender': 'female'},
        'Draco Malfoy': {'name': 'Draconia Malfoy', 'gender': 'female'}
    }
    """
    with open(character_file, 'r') as f:
        data = json.load(f)
    
    characters = data.get('characters', data)
    custom_characters = {}
    
    for name, info in characters.items():
        # Skip generic terms
        if name in {'They', 'Something', 'Someone', 'Everyone', 'Anyone', 'Nobody', 'People'}:
            continue
        
        # Apply specific mapping if provided
        if specific_mappings and name in specific_mappings:
            custom_info = {**info, **specific_mappings[name]}
        else:
            # Default transformation
            custom_info = {
                'name': info['name'],
                'gender': target_gender,
                'role': info.get('role', f"Character with {info.get('mentions', 0)} mentions"),
                'mentions': info.get('mentions', []),
                'name_variants': info.get('variants', [])
            }
        
        custom_characters[name] = custom_info
    
    return custom_characters


# Example CLI integration points
def cli_additions():
    """
    Proposed additions to regender_book_cli.py
    """
    additions = """
    # In argument parser section:
    
    # Add --characters option to transform command
    transform_parser.add_argument('--characters', help='Pre-analyzed character file to use')
    
    # Add new analyze-characters command
    analyze_parser = subparsers.add_parser('analyze-characters', help='Analyze and save character data')
    analyze_parser.add_argument('input', help='Input JSON book file')
    analyze_parser.add_argument('-o', '--output', required=True, help='Output character file')
    analyze_parser.add_argument('--model', default='gpt-4o-mini', help='Model to use')
    analyze_parser.add_argument('--provider', choices=['openai', 'grok', 'mlx'], help='LLM provider')
    
    # In command execution section:
    
    elif args.command == 'analyze-characters':
        from tests.test_character_cli_integration import analyze_characters_command
        analyze_characters_command(args.input, args.output, args.model, args.provider)
    
    # In transform_single_book function, add character_file parameter:
    # And use transform_with_characters_wrapper instead of transform_book directly
    """
    return additions


if __name__ == '__main__':
    print("📋 Character-based Transformation CLI Integration Design\n")
    print("This file demonstrates the proposed integration approach.\n")
    print("Key features:")
    print("1. --characters option for transform command")
    print("2. New analyze-characters command")
    print("3. Backward compatible with existing functionality")
    print("4. Clean separation of concerns")
    print("\nSee function docstrings for usage examples.")