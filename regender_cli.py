#!/usr/bin/env python3
"""
Regender CLI - Transform gender representation in literature

This CLI uses the modern service-oriented architecture to process books,
analyze characters, and apply gender transformations.
"""

import argparse
import asyncio
import os
import sys
import logging
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add src to path for new architecture
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import Application


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def process_book(args):
    """Process book using the service-oriented architecture."""
    # Initialize application
    config_path = args.config or "src/config.json"
    app = Application(config_path)
    
    # Determine input and output paths
    input_path = args.input
    output_path = args.output
    
    if not output_path:
        # Generate output path based on input and transform type
        input_file = Path(input_path)
        if args.transform_type == 'parse_only':
            # For parsing: keep in books/json/ with same name
            if 'texts' in str(input_file.parent):
                output_dir = Path(str(input_file.parent).replace('texts', 'json'))
            else:
                output_dir = input_file.parent
            output_path = output_dir / f"{input_file.stem}.json"
        elif args.transform_type == 'character_analysis':
            # For character analysis: add -characters suffix
            if input_file.suffix == '.json':
                # Input is already JSON, add -characters
                output_path = input_file.parent / f"{input_file.stem}-characters.json"
            else:
                # Input is text, put in json/ dir with -characters
                if 'texts' in str(input_file.parent):
                    output_dir = Path(str(input_file.parent).replace('texts', 'json'))
                else:
                    output_dir = input_file.parent
                output_path = output_dir / f"{input_file.stem}-characters.json"
        else:
            # For transformations: add transformation type
            output_path = input_file.parent / f"{input_file.stem}_{args.transform_type}.json"
    
    # Check mode
    if args.transform_type == 'parse_only':
        print(f"Parsing {input_path} to canonical JSON format...")
        result = app.parse_book_sync(
            file_path=input_path,
            output_path=str(output_path)
        )
    elif args.transform_type == 'character_analysis':
        print(f"Analyzing characters in {input_path}...")
        result = app.analyze_characters_sync(
            file_path=input_path,
            output_path=str(output_path)
        )
    else:
        # Process the book with transformation
        print(f"Processing {input_path} with {args.transform_type} transformation...")
        result = app.process_book_sync(
            file_path=input_path,
            transform_type=args.transform_type,
            output_path=str(output_path),
            quality_control=not args.no_qc
        )
    
    # Display results
    if result['success']:
        print(f"\n✅ Success!")
        print(f"  Book: {result['book_title']}")
        if args.transform_type == 'parse_only':
            print(f"  Chapters: {result.get('chapters', 'N/A')}")
            print(f"  Paragraphs: {result.get('paragraphs', 'N/A')}")
            print(f"  Sentences: {result.get('sentences', 'N/A')}")
        elif args.transform_type == 'character_analysis':
            print(f"  Total characters: {result.get('total_characters', 0)}")
            print(f"  By gender: {result.get('by_gender', {})}")
            print(f"  By importance: {result.get('by_importance', {})}")
            if result.get('main_characters'):
                print(f"  Main characters: {', '.join(result['main_characters'][:5])}")
        else:
            print(f"  Characters: {result['characters']}")
            print(f"  Changes: {result['changes']}")
            if result.get('quality_score'):
                print(f"  Quality: {result['quality_score']}/100")
        print(f"  Output: {result['output_path']}")
    else:
        print(f"\n❌ Error: {result['error']}")
        sys.exit(1)
    
    # Clean up
    app.shutdown()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Regender-XYZ CLI - Transform gender representation in literature"
    )
    
    # Main arguments
    parser.add_argument(
        'input',
        help='Input file path (text or JSON)'
    )
    
    parser.add_argument(
        'transform_type',
        choices=['all_male', 'all_female', 'gender_swap', 'nonbinary', 'parse_only', 'character_analysis'],
        help='Type of transformation to apply (use parse_only for JSON, character_analysis for character detection)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file path (defaults to input_name_transform_type.json)'
    )
    
    # Configuration options
    parser.add_argument(
        '--config',
        help='Path to configuration file (default: src/config.json)'
    )
    
    parser.add_argument(
        '--no-qc',
        action='store_true',
        help='Skip quality control'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Process the book
    process_book(args)


if __name__ == '__main__':
    main()