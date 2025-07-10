#!/usr/bin/env python3
"""
Book processing and gender transformation CLI for regender-xyz.

This CLI provides a complete pipeline for:
1. Downloading books from Project Gutenberg
2. Converting them to JSON format
3. Transforming gender representation
4. Converting back to text format
"""

import argparse
import json
import sys
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Import book processing modules
from gutenberg import GutenbergDownloader
from book_parser import BookParser, BookValidator, process_all_books, recreate_text_from_json, save_book_json, load_book_json
from book_transform import transform_book

# CLI styling
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'


def print_banner():
    """Print a fancy banner."""
    banner = f"""
{CYAN}╔══════════════════════════════════════════════════╗
║             {BOLD}ReGender Book CLI v1.0{RESET}{CYAN}               ║
║     Transform Gender in Literature with AI        ║
╚══════════════════════════════════════════════════╝{RESET}
"""
    print(banner)


# =============================================================================
# Gutenberg Download Functions
# =============================================================================

def download_books(count=100, output_dir="books/texts"):
    """Download top books from Project Gutenberg."""
    print(f"\n📚 Downloading top {count} books from Project Gutenberg...")
    print("=" * 70)
    
    downloader = GutenbergDownloader(output_dir=output_dir)
    stats = downloader.download_top_books(limit=count)
    
    print("\n" + "=" * 70)
    print("✅ Download Complete!")
    print(f"📊 Downloaded: {stats['successful']} books")
    print(f"❌ Failed: {stats['failed']} books")
    print(f"💾 Total size: {stats['total_size']}")
    
    return stats


def list_books(texts_dir="books/texts"):
    """List all downloaded books."""
    texts_path = Path(texts_dir)
    if not texts_path.exists():
        print(f"{RED}❌ Directory '{texts_dir}' not found{RESET}")
        return
    
    text_files = sorted(texts_path.glob("*.txt"))
    if not text_files:
        print(f"{RED}❌ No text files found in '{texts_dir}'{RESET}")
        return
    
    print(f"\n📚 Found {len(text_files)} books in {texts_dir}/")
    print("=" * 70)
    
    for i, file in enumerate(text_files, 1):
        # Extract book info from filename (pg####-Title.txt)
        match = re.match(r'pg(\d+)-(.+)\.txt', file.name)
        if match:
            book_id, title = match.groups()
            print(f"{i:3d}. [{book_id}] {title}")
        else:
            print(f"{i:3d}. {file.name}")
    
    print(f"\n💡 Tip: Use 'python {sys.argv[0]} transform books/texts/[filename]' to process individual books")


# =============================================================================
# Book Processing Functions
# =============================================================================

def process_books(input_dir="books/texts", output_dir="books/json"):
    """Process all downloaded books to JSON format."""
    print("\n🔄 Processing books to JSON format...")
    print("=" * 70)
    
    stats = process_all_books(
        input_dir=input_dir,
        output_dir=output_dir
    )
    
    print("\n" + "=" * 70)
    print("✅ Processing Complete!")
    print(f"📊 Successful: {stats['successful']} books")
    print(f"❌ Failed: {stats['failed']} books")
    if stats['successful'] > 0:
        print(f"📖 Avg chapters/book: {stats['total_chapters']/stats['successful']:.1f}")
        print(f"📝 Avg sentences/book: {stats['total_sentences']/stats['successful']:.0f}")
    
    return stats


def validate_books(texts_dir="books/texts", json_dir="books/json", report="validation_report.txt"):
    """Validate JSON files against source texts."""
    print("\n🔍 Validating JSON representations...")
    print("=" * 70)
    
    validator = BookValidator(texts_dir, json_dir)
    results = validator.validate_all()
    validator.generate_report(results, report)
    
    print("\n" + "=" * 70)
    print(f"✅ Valid: {results['valid_books']}/{results['total_books']} books")
    print(f"❌ Invalid: {results['invalid_books']} books")
    print(f"⚠️  Warnings: {results['books_with_warnings']} books")
    print(f"📄 Report: {report}")
    
    return results


# =============================================================================
# Gender Transformation Functions
# =============================================================================

def load_json_book(file_path: str) -> Dict[str, Any]:
    """Load a JSON book file."""
    try:
        return load_book_json(file_path)
    except Exception as e:
        print(f"{RED}Error loading JSON file: {e}{RESET}")
        sys.exit(1)


def save_json_book(data: Dict[str, Any], output_path: str):
    """Save transformed book as JSON."""
    try:
        save_book_json(data, output_path)
        print(f"{GREEN}✓ Saved transformed JSON to: {output_path}{RESET}")
    except Exception as e:
        print(f"{RED}Error saving JSON file: {e}{RESET}")
        sys.exit(1)


def transform_single_book(input_file: str, output_file: Optional[str] = None, 
                         text_output: Optional[str] = None, transform_type: str = "comprehensive",
                         model: str = "gpt-4o-mini", provider: Optional[str] = None, 
                         character_file: Optional[str] = None, quiet: bool = False):
    """Transform a single JSON book."""
    if not quiet:
        print(f"\n{CYAN}📖 Processing: {input_file}{RESET}")
        print("=" * 60)
    
    # Load the book
    book_data = load_json_book(input_file)
    
    # Get book info
    title = book_data.get('metadata', {}).get('title', 'Unknown Title')
    author = book_data.get('metadata', {}).get('author', 'Unknown Author')
    chapters = len(book_data.get('chapters', []))
    
    if not quiet:
        print(f"📚 Title: {title}")
        print(f"✍️  Author: {author}")
        print(f"📑 Chapters: {chapters}")
        print(f"🔄 Transform: {transform_type}")
        
        # Get the actual model being used by the provider
        if provider:
            try:
                from api_client import UnifiedLLMClient
                temp_client = UnifiedLLMClient(provider=provider)
                actual_model = temp_client.get_default_model()
                print(f"🤖 Model: {actual_model}")
                print(f"🏭 Provider: {provider}")
            except:
                print(f"🤖 Model: {model}")
                print(f"🏭 Provider: {provider}")
        else:
            print(f"🤖 Model: {model}")
    
    if character_file and not quiet:
        print(f"📋 Characters: {character_file}")
    
    # Transform the book
    try:
        # Use actual model name from provider if available
        actual_model = model
        if provider:
            try:
                from api_client import UnifiedLLMClient
                temp_client = UnifiedLLMClient(provider=provider)
                actual_model = temp_client.get_default_model()
            except:
                pass
        
        start_time = time.time()
        
        if character_file:
            # Use character-based transformation
            from book_transform.utils import transform_with_characters
            transformed_data = transform_with_characters(
                book_data,
                character_file=character_file,
                transform_type=transform_type,
                model=actual_model,
                provider=provider,
                verbose=not quiet
            )
        else:
            # Standard transformation
            transformed_data = transform_book(
                book_data,
                transform_type=transform_type,
                model=actual_model,
                provider=provider,
                verbose=not quiet
            )
        
        elapsed = time.time() - start_time
        
        if not quiet:
            print(f"\n{GREEN}✓ Transformation complete in {elapsed:.1f}s{RESET}")
        
        # Save JSON output
        if output_file:
            save_json_book(transformed_data, output_file)
        
        # Generate text output if requested
        if text_output:
            if not quiet:
                print(f"\n📝 Converting to text format...")
            recreate_text_from_json(output_file, text_output, verbose=False)
            if not quiet:
                print(f"{GREEN}✓ Saved text to: {text_output}{RESET}")
        
        return transformed_data
        
    except Exception as e:
        print(f"{RED}Error during transformation: {e}{RESET}")
        sys.exit(1)


def analyze_characters_command(input_file: str, output_file: str, 
                              model: str = "gpt-4o-mini", provider: Optional[str] = None):
    """Analyze and save character data from a book."""
    print(f"\n{CYAN}📖 Analyzing characters in: {input_file}{RESET}")
    
    # Load book
    book_data = load_json_book(input_file)
    
    # Analyze characters
    from book_characters import analyze_book_characters
    characters, context = analyze_book_characters(
        book_data,
        model=model,
        provider=provider,
        verbose=True
    )
    
    # Save character data
    character_data = {
        'metadata': {
            'source_book': input_file,
            'analysis_model': model,
            'analysis_provider': provider,
            'character_count': len(characters)
        },
        'characters': characters,
        'context': context
    }
    
    save_json_book(character_data, output_file)
    
    print(f"\n{GREEN}✓ Saved {len(characters)} characters to: {output_file}{RESET}")
    return characters


def batch_transform(input_dir: str = "books/json", output_dir: str = "books/output",
                   transform_type: str = "comprehensive", model: str = "gpt-4o-mini",
                   provider: Optional[str] = None, limit: Optional[int] = None):
    """Transform multiple JSON books."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Find all JSON files
    json_files = sorted(input_path.glob("*.json"))
    if limit:
        json_files = json_files[:limit]
    
    if not json_files:
        print(f"{RED}No JSON files found in {input_dir}{RESET}")
        return
    
    print(f"\n{CYAN}🔄 Batch transforming {len(json_files)} books{RESET}")
    print("=" * 60)
    print(f"Transform type: {transform_type}")
    
    # Get the actual model being used by the provider
    if provider:
        try:
            from api_client import UnifiedLLMClient
            temp_client = UnifiedLLMClient(provider=provider)
            actual_model = temp_client.get_default_model()
            print(f"Model: {actual_model}")
            print(f"Provider: {provider}")
        except:
            print(f"Model: {model}")
            print(f"Provider: {provider}")
    else:
        print(f"Model: {model}")
    print(f"Output directory: {output_dir}")
    print("=" * 60)
    
    successful = 0
    failed = 0
    
    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] Processing {json_file.name}")
        
        output_file = output_path / f"{json_file.stem}_transformed.json"
        
        try:
            transform_single_book(
                str(json_file),
                str(output_file),
                transform_type=transform_type,
                model=model,
                provider=provider,
                quiet=True
            )
            successful += 1
            print(f"{GREEN}✓ Success{RESET}")
        except Exception as e:
            failed += 1
            print(f"{RED}✗ Failed: {e}{RESET}")
    
    print("\n" + "=" * 60)
    print(f"{GREEN}✓ Successful: {successful}{RESET}")
    if failed > 0:
        print(f"{RED}✗ Failed: {failed}{RESET}")
    print(f"📁 Output directory: {output_dir}")


# =============================================================================
# Pipeline Functions
# =============================================================================

def pipeline(count=100, transform_type="comprehensive", model="gpt-4o-mini"):
    """Run the complete pipeline: download, process, and transform."""
    print("\n🚀 Running complete book processing pipeline...")
    print("=" * 70)
    
    # Download
    download_stats = download_books(count)
    
    if download_stats['successful'] == 0:
        print(f"{RED}❌ No books downloaded, aborting pipeline{RESET}")
        return
    
    # Process to JSON
    print("\n" + "=" * 70)
    process_stats = process_books()
    
    if process_stats['successful'] == 0:
        print(f"{RED}❌ No books processed to JSON, aborting pipeline{RESET}")
        return
    
    # Transform
    print("\n" + "=" * 70)
    batch_transform(transform_type=transform_type, model=model)
    
    print("\n" + "=" * 70)
    print("🎉 Pipeline Complete!")
    print(f"📚 Transformed books ready in: book_transforms/")


# =============================================================================
# Main CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Book processing and gender transformation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download books from Project Gutenberg')
    download_parser.add_argument('--count', type=int, default=100, help='Number of books to download')
    download_parser.add_argument('--output', default='books/texts', help='Output directory')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List downloaded books')
    list_parser.add_argument('--dir', default='books/texts', help='Directory to list')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Convert books to JSON format')
    process_parser.add_argument('--input', default='books/texts', help='Input directory')
    process_parser.add_argument('--output', default='books/json', help='Output directory')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate JSON against source texts')
    validate_parser.add_argument('--texts-dir', default='books/texts', help='Directory with source texts')
    validate_parser.add_argument('--json-dir', default='books/json', help='Directory with JSON files')
    validate_parser.add_argument('--report', default='validation_report.txt', help='Report filename')
    
    # Transform command
    transform_parser = subparsers.add_parser('transform', help='Transform gender in books')
    transform_parser.add_argument('input', help='Input JSON file or directory')
    transform_parser.add_argument('-o', '--output', help='Output JSON file or directory')
    transform_parser.add_argument('-t', '--text', help='Also generate text output')
    transform_parser.add_argument('--type', choices=['all_male', 'all_female', 'gender_swap'], 
                                default='gender_swap', help='Gender transformation mode')
    transform_parser.add_argument('--model', help='Model to use (defaults to provider\'s default)')
    transform_parser.add_argument('--provider', choices=['openai', 'grok', 'mlx'], help='LLM provider to use')
    transform_parser.add_argument('--characters', help='Pre-analyzed character file to use')
    transform_parser.add_argument('--batch', action='store_true', help='Process directory of files')
    transform_parser.add_argument('--limit', type=int, help='Limit number of files in batch mode')
    
    # Analyze characters command
    analyze_parser = subparsers.add_parser('analyze-characters', help='Analyze and save character data')
    analyze_parser.add_argument('input', help='Input JSON book file')
    analyze_parser.add_argument('-o', '--output', required=True, help='Output character file')
    analyze_parser.add_argument('--model', help='Model to use (defaults to provider\'s default)')
    analyze_parser.add_argument('--provider', choices=['openai', 'grok', 'mlx'], help='LLM provider')
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Run complete pipeline')
    pipeline_parser.add_argument('--count', type=int, default=100, help='Number of books to download')
    pipeline_parser.add_argument('--type', choices=['all_male', 'all_female', 'gender_swap'],
                               default='gender_swap', help='Gender transformation mode')
    pipeline_parser.add_argument('--model', help='Model to use (defaults to provider\'s default)')
    
    args = parser.parse_args()
    
    if not args.command:
        print_banner()
        parser.print_help()
        return
    
    # Execute commands
    if args.command == 'download':
        download_books(args.count, args.output)
    
    elif args.command == 'list':
        list_books(args.dir)
    
    elif args.command == 'process':
        process_books(args.input, args.output)
    
    elif args.command == 'validate':
        validate_books(args.texts_dir, args.json_dir, args.report)
    
    elif args.command == 'transform':
        if args.batch or Path(args.input).is_dir():
            # Batch mode
            output_dir = args.output or 'books/output'
            batch_transform(args.input, output_dir, args.type, args.model, args.provider, args.limit)
        else:
            # Single file mode
            output_file = args.output
            if not output_file:
                input_path = Path(args.input)
                output_file = str(input_path.parent / f"{input_path.stem}_transformed.json")
            
            transform_single_book(args.input, output_file, args.text, args.type, args.model, args.provider, args.characters)
    
    elif args.command == 'analyze-characters':
        analyze_characters_command(args.input, args.output, args.model, args.provider)
    
    elif args.command == 'pipeline':
        pipeline(args.count, args.type, args.model)


if __name__ == "__main__":
    main()