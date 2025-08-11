#!/usr/bin/env python3
"""
Regender CLI v2 - New Architecture

This CLI uses the new service-oriented architecture from Phase 3.
It can be enabled with the --use-new-architecture flag or
by setting the USE_NEW_ARCHITECTURE environment variable.
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


def process_book_new_architecture(args):
    """Process book using new architecture."""
    # Initialize application
    config_path = args.config or "config/app.json"
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
        description="Regender-XYZ CLI v2 - Transform gender representation in literature"
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
        help='Path to configuration file (default: config/app.json)'
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
    
    # Architecture selection
    parser.add_argument(
        '--use-new-architecture',
        action='store_true',
        help='Use the new service-oriented architecture'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Check if we should use new architecture
    use_new = args.use_new_architecture or os.getenv('USE_NEW_ARCHITECTURE', '').lower() == 'true'
    
    if use_new:
        print("Using new service-oriented architecture...")
        process_book_new_architecture(args)
    else:
        # Fall back to old architecture
        print("Using legacy architecture (use --use-new-architecture for new version)...")
        
        # Import and use old CLI
        try:
            from regender_book_cli import main as legacy_main
            
            # Build legacy arguments
            legacy_args = [
                'transform',
                args.input,
                '--type', args.transform_type
            ]
            
            if args.output:
                legacy_args.extend(['--output', args.output])
            
            if args.verbose:
                legacy_args.append('--verbose')
            
            # Modify sys.argv for legacy CLI
            old_argv = sys.argv
            sys.argv = ['regender_book_cli.py'] + legacy_args
            
            try:
                legacy_main()
            finally:
                sys.argv = old_argv
                
        except ImportError:
            print("Error: Legacy CLI not found. Please use --use-new-architecture")
            sys.exit(1)


if __name__ == '__main__':
    main()