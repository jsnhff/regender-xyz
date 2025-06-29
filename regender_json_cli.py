#!/usr/bin/env python3
"""
JSON-based gender transformation CLI for regender-xyz.

This CLI processes pre-cleaned JSON books created by the preprocess command,
transforming gender representation chapter by chapter.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
import time
from datetime import datetime

from json_transform import transform_json_book
from book_to_json import recreate_text_from_json

# CLI styling
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'


def load_json_book(file_path: str) -> Dict[str, Any]:
    """Load a JSON book file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"{RED}Error loading JSON file: {e}{RESET}")
        sys.exit(1)


def save_json_book(data: Dict[str, Any], output_path: str):
    """Save transformed book as JSON."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"{GREEN}✓ Saved transformed JSON to: {output_path}{RESET}")
    except Exception as e:
        print(f"{RED}Error saving JSON file: {e}{RESET}")
        sys.exit(1)


def print_banner():
    """Print the CLI banner."""
    print(f"""
{CYAN}╭─────────────────────────────────────╮
│  {BOLD}Regender JSON Transformer v0.1.0{RESET}{CYAN}  │
│  Chapter-by-Chapter Processing      │
╰─────────────────────────────────────╯{RESET}
""")


def print_book_info(book_data: Dict[str, Any]):
    """Print book information."""
    metadata = book_data.get('metadata', {})
    stats = book_data.get('statistics', {})
    
    print(f"\n{BOLD}Book Information:{RESET}")
    print(f"  Title: {metadata.get('title', 'Unknown')}")
    print(f"  Author: {metadata.get('author', 'Unknown')}")
    print(f"  Chapters: {stats.get('total_chapters', 0)}")
    print(f"  Sentences: {stats.get('total_sentences', 0):,}")
    print(f"  Words: {stats.get('total_words', 0):,}")


def main():
    parser = argparse.ArgumentParser(
        description='Transform gender in pre-processed JSON books',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s book_clean.json -t feminine
  %(prog)s book_clean.json -t masculine -o book_masc.json
  %(prog)s book_clean.json -t neutral --recreate --model gpt-4
"""
    )
    
    parser.add_argument('input', help='Input JSON book file')
    parser.add_argument('-t', '--type', required=True,
                        choices=['feminine', 'masculine', 'neutral'],
                        help='Type of gender transformation')
    parser.add_argument('-o', '--output', help='Output JSON file (default: input_transformed.json)')
    parser.add_argument('-r', '--recreate', action='store_true',
                        help='Also create a text file from transformed JSON')
    parser.add_argument('-m', '--model', default='gpt-4o-mini',
                        help='OpenAI model to use (default: gpt-4o-mini)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Show detailed progress')
    parser.add_argument('--dry-run', action='store_true',
                        help='Process only the first chapter as a test')
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input)
        output_path = str(input_path.parent / f"{input_path.stem}_transformed.json")
    
    # Load the JSON book
    print(f"\n{CYAN}Loading JSON book...{RESET}")
    book_data = load_json_book(args.input)
    print_book_info(book_data)
    
    # Transform the book
    print(f"\n{CYAN}Starting {args.type} transformation...{RESET}")
    start_time = time.time()
    
    try:
        transformed_data = transform_json_book(
            book_data,
            transform_type=args.type,
            model=args.model,
            verbose=args.verbose,
            dry_run=args.dry_run
        )
        
        # Update metadata
        transformed_data['metadata']['transformation'] = {
            'type': args.type,
            'model': args.model,
            'timestamp': datetime.now().isoformat(),
            'source_file': args.input
        }
        
        # Save the transformed JSON
        save_json_book(transformed_data, output_path)
        
        # Print summary
        elapsed = time.time() - start_time
        stats = transformed_data.get('statistics', {})
        print(f"\n{BOLD}Transformation Complete:{RESET}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Changes: {stats.get('total_changes', 0):,}")
        print(f"  Output: {output_path}")
        
        # Recreate text if requested
        if args.recreate:
            text_output = output_path.replace('.json', '.txt')
            print(f"\n{CYAN}Recreating text file...{RESET}")
            recreate_text_from_json(output_path, text_output, verbose=False)
            print(f"{GREEN}✓ Text file created: {text_output}{RESET}")
            
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Transformation interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Error during transformation: {e}{RESET}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()