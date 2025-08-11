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
        output_path = input_file.parent / f"{input_file.stem}_{args.transform_type}.json"
    
    # Process the book
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
        choices=['all_male', 'all_female', 'gender_swap', 'nonbinary'],
        help='Type of transformation to apply'
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