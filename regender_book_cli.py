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
from book_downloader import GutenbergDownloader
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

def download_books(book_id=None, count=100, output_dir="books/texts"):
    """Download books from Project Gutenberg."""
    downloader = GutenbergDownloader(output_dir=output_dir)
    
    if book_id:
        # Download specific book
        print(f"\n📚 Downloading book ID {book_id} from Project Gutenberg...")
        print("=" * 70)
        
        try:
            success = downloader.download_book(int(book_id))
            if success:
                print(f"\n✅ Successfully downloaded book ID {book_id}")
                return {'successful': 1, 'failed': 0}
            else:
                print(f"\n❌ Failed to download book ID {book_id}")
                return {'successful': 0, 'failed': 1}
        except Exception as e:
            print(f"\n❌ Error downloading book ID {book_id}: {e}")
            return {'successful': 0, 'failed': 1}
    else:
        # Download top books
        print(f"\n📚 Downloading top {count} books from Project Gutenberg...")
        print("=" * 70)
        
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

def process_books(input_path=None, output_path=None):
    """Process books to JSON format (single file or directory)."""
    # Default paths
    if not input_path:
        input_path = "books/texts"
    if not output_path:
        output_path = "books/json" if Path(input_path).is_dir() else None
    
    input_p = Path(input_path)
    
    if input_p.is_file():
        # Process single file
        print(f"\n🔄 Processing single book to JSON format...")
        print("=" * 70)
        
        # Determine output file
        if output_path:
            output_file = Path(output_path)
        else:
            # Create output filename in same directory
            output_file = input_p.with_suffix('').parent / f"{input_p.stem}_clean.json"
        
        # Create output directory if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Process the file
        parser = BookParser()
        try:
            book_data = parser.parse_file(str(input_p))
            save_book_json(book_data, str(output_file))
            
            print(f"✓ Successfully processed: {input_p.name}")
            print(f"  Output: {output_file}")
            print(f"  Chapters: {len(book_data.get('chapters', []))}")
            print(f"  Sentences: {book_data.get('statistics', {}).get('total_sentences', 0)}")
            
        except Exception as e:
            print(f"❌ Failed to process {input_p.name}: {e}")
            
    else:
        # Process directory
        print("\n🔄 Processing books to JSON format...")
        print("=" * 70)
        
        stats = process_all_books(
            input_dir=str(input_path),
            output_dir=str(output_path) if output_path else "books/json"
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
    # Check for model/provider mismatch
    if model != "gpt-4o-mini" and not provider:
        detected_provider = detect_provider_from_model(model)
        if detected_provider:
            print(f"{RED}❌ Model '{model}' requires provider '{detected_provider}'{RESET}")
            print(f"{YELLOW}Please add: --provider {detected_provider}{RESET}")
            sys.exit(1)
        else:
            print(f"{RED}❌ Cannot determine provider for model '{model}'{RESET}")
            print(f"{YELLOW}Please specify a provider with: --provider [openai|anthropic|grok]{RESET}")
            sys.exit(1)
    
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
                              model: str = "gpt-4o-mini", provider: Optional[str] = None,
                              rate_limited: bool = False, tokens_per_minute: int = 16000):
    """Analyze and save character data from a book."""
    # Check for model/provider mismatch
    if model != "gpt-4o-mini" and not provider:
        detected_provider = detect_provider_from_model(model)
        if detected_provider:
            print(f"{RED}❌ Model '{model}' requires provider '{detected_provider}'{RESET}")
            print(f"{YELLOW}Please add: --provider {detected_provider}{RESET}")
            sys.exit(1)
        else:
            print(f"{RED}❌ Cannot determine provider for model '{model}'{RESET}")
            print(f"{YELLOW}Please specify a provider with: --provider [openai|anthropic|grok]{RESET}")
            sys.exit(1)
    
    print(f"\n{CYAN}📖 Analyzing characters in: {input_file}{RESET}")
    
    # Load book
    book_data = load_json_book(input_file)
    
    # Auto-enable rate limiting for grok-4-latest
    if model == "grok-4-latest" or (provider == "grok" and "4" in str(model)):
        if not rate_limited:
            print(f"{YELLOW}⚠️  Auto-enabling rate limiting for {model} (16k tokens/minute){RESET}")
            rate_limited = True
    
    # Analyze characters
    if rate_limited:
        from book_characters import analyze_book_with_rate_limits
        print(f"{CYAN}🔧 Using rate-limited analysis ({tokens_per_minute:,} tokens/minute){RESET}")
        characters = analyze_book_with_rate_limits(
            input_file,
            output_file,
            model=model,
            provider=provider,
            tokens_per_minute=tokens_per_minute,
            verbose=True
        )
        # Results are already saved by analyze_book_with_rate_limits
        print(f"\n{GREEN}✅ Character analysis complete!{RESET}")
    else:
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
    # Check for model/provider mismatch
    if model != "gpt-4o-mini" and not provider:
        detected_provider = detect_provider_from_model(model)
        if detected_provider:
            print(f"{RED}❌ Model '{model}' requires provider '{detected_provider}'{RESET}")
            print(f"{YELLOW}Please add: --provider {detected_provider}{RESET}")
            return
        else:
            print(f"{RED}❌ Cannot determine provider for model '{model}'{RESET}")
            print(f"{YELLOW}Please specify a provider with: --provider [openai|anthropic|grok]{RESET}")
            return
    
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
# Unified Regender Command (NEW)
# =============================================================================

def detect_provider_from_model(model_name: str) -> Optional[str]:
    """Detect provider from model name."""
    if not model_name:
        return None
    
    model_lower = model_name.lower()
    if 'gpt' in model_lower:
        return 'openai'
    elif 'claude' in model_lower:
        return 'anthropic'
    elif 'grok' in model_lower:
        return 'grok'
    return None


def handle_regender_command(args):
    """Handle the unified regender command that does everything."""
    from book_transform import transform_book_unified
    from book_parser import BookParser, save_book_json, load_book_json
    
    # Check for model/provider mismatch
    if args.model and not args.provider:
        detected_provider = detect_provider_from_model(args.model)
        if detected_provider:
            print(f"{RED}❌ Model '{args.model}' requires provider '{detected_provider}'{RESET}")
            print(f"{YELLOW}Please add: --provider {detected_provider}{RESET}")
            return
        else:
            print(f"{RED}❌ Cannot determine provider for model '{args.model}'{RESET}")
            print(f"{YELLOW}Please specify a provider with: --provider [openai|anthropic|grok]{RESET}")
            return
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"{RED}❌ Input file not found: {input_path}{RESET}")
        return
    
    print(f"\n{CYAN}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}Unified Regender Transformation{RESET}")
    print(f"{CYAN}{'='*60}{RESET}")
    
    # Determine if input is text or JSON
    if input_path.suffix == '.txt':
        # Need to parse text to JSON first
        print(f"\n{BOLD}Step 1: Parsing text to JSON{RESET}")
        parser = BookParser()
        book_data = parser.parse_file(str(input_path))
        
        if not book_data:
            print(f"{RED}❌ Failed to parse text file{RESET}")
            return
            
        print(f"  ✓ Successfully parsed: {book_data.get('title', 'Unknown')}")
        
    elif input_path.suffix == '.json':
        # Load existing JSON
        print(f"\n{BOLD}Loading JSON file{RESET}")
        book_data = load_book_json(str(input_path))
        
        if not book_data:
            print(f"{RED}❌ Failed to load JSON file{RESET}")
            return
            
        print(f"  ✓ Loaded: {book_data.get('title', 'Unknown')}")
    else:
        print(f"{RED}❌ Input must be .txt or .json file{RESET}")
        return
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Auto-generate output path
        output_dir = input_path.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        base_name = input_path.stem.replace('_clean', '').replace('_transformed', '')
        output_path = str(output_dir / f"{base_name}_{args.type}")
    
    print(f"\n{BOLD}Output will be saved to:{RESET}")
    print(f"  📄 JSON: {output_path}.json")
    print(f"  📝 Text: {output_path}.txt")
    
    # Run unified transformation
    try:
        if args.dry_run:
            print(f"\n{YELLOW}🔬 DRY RUN MODE - Processing first chapter only{RESET}")
        
        transformed_book, report = transform_book_unified(
            book_data=book_data,
            transform_type=args.type,
            model=args.model,
            provider=args.provider,
            output_path=output_path,
            verbose=True,
            dry_run=args.dry_run
        )
        
        # Show summary
        print(f"\n{GREEN}{'='*60}{RESET}")
        print(f"{GREEN}{BOLD}Transformation Summary{RESET}")
        print(f"{GREEN}{'='*60}{RESET}")
        print(f"📊 Quality Score: {report['stages']['validation']['quality_score']}/100")
        print(f"✏️  Total Changes: {transformed_book['transformation']['total_changes']}")
        print(f"⏱️  Total Time: {report['total_time']:.1f}s")
        print(f"\n✅ Files saved to:")
        print(f"   {output_path}.json")
        print(f"   {output_path}.txt")
        
    except Exception as e:
        print(f"\n{RED}❌ Transformation failed: {e}{RESET}")
        import traceback
        traceback.print_exc()


# =============================================================================
# Pipeline Functions
# =============================================================================

def pipeline(count=100, transform_type="comprehensive", model="gpt-4o-mini"):
    """Run the complete pipeline: download, process, and transform."""
    print(f"\n{YELLOW}{BOLD}⚠️  WARNING: The 'pipeline' command is deprecated!{RESET}")
    print(f"{YELLOW}Please use the 'regender' command instead for better results.{RESET}")
    print(f"{YELLOW}Example: python {sys.argv[0]} regender book.txt --type {transform_type}{RESET}")
    print("\nContinuing with deprecated pipeline...\n")
    
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
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick transform a single book
  %(prog)s regender book.txt --type all_female
  
  # Download specific books from Project Gutenberg
  %(prog)s download --count 5
  
  # Process text files to JSON
  %(prog)s process --input texts/ --output json/
  
  # Transform with high quality
  %(prog)s regender book.json --quality high --provider anthropic
  
  # List available books
  %(prog)s list

For more help on specific commands:
  %(prog)s <command> --help
""")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download books from Project Gutenberg')
    download_parser.add_argument('book_id', nargs='?', help='Specific book ID to download (e.g., 1342 for Pride and Prejudice)')
    download_parser.add_argument('--count', type=int, default=100, help='Number of top books to download (if no book_id specified)')
    download_parser.add_argument('--output', default='books/texts', help='Output directory')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List downloaded books')
    list_parser.add_argument('--dir', default='books/texts', help='Directory to list')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Convert books to JSON format')
    process_parser.add_argument('input', nargs='?', help='Input file or directory (default: books/texts)')
    process_parser.add_argument('-o', '--output', help='Output file or directory')
    
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
    transform_parser.add_argument('--provider', choices=['openai', 'anthropic', 'claude', 'grok'], help='LLM provider to use')
    transform_parser.add_argument('--characters', help='Pre-analyzed character file to use')
    transform_parser.add_argument('--batch', action='store_true', help='Process directory of files')
    transform_parser.add_argument('--limit', type=int, help='Limit number of files in batch mode')
    
    # Analyze characters command
    analyze_parser = subparsers.add_parser('analyze-characters', help='Analyze and save character data')
    analyze_parser.add_argument('input', help='Input JSON book file')
    analyze_parser.add_argument('-o', '--output', required=True, help='Output character file')
    analyze_parser.add_argument('--model', help='Model to use (defaults to provider\'s default)')
    analyze_parser.add_argument('--provider', choices=['openai', 'anthropic', 'claude', 'grok'], help='LLM provider')
    analyze_parser.add_argument('--rate-limited', action='store_true', 
                               help='Use rate-limited analysis (auto-enabled for grok-4-latest)')
    analyze_parser.add_argument('--tokens-per-minute', type=int, default=16000,
                               help='Token rate limit per minute (default: 16000)')
    
    # Unified regender command (NEW - RECOMMENDED)
    regender_parser = subparsers.add_parser('regender', help='Complete transformation with quality control')
    regender_parser.add_argument('input', help='Input text file or JSON file')
    regender_parser.add_argument('-o', '--output', help='Output path (without extension)')
    regender_parser.add_argument('--type', choices=['all_male', 'all_female', 'gender_swap'],
                               default='gender_swap', help='Gender transformation mode')
    regender_parser.add_argument('--model', help='Model to use')
    regender_parser.add_argument('--provider', choices=['openai', 'anthropic', 'claude', 'grok'], help='LLM provider')
    regender_parser.add_argument('--dry-run', action='store_true', help='Test without using API credits (processes first chapter only)')
    
    # Pipeline command (DEPRECATED - use 'regender' instead)
    pipeline_parser = subparsers.add_parser('pipeline', help='[DEPRECATED] Use regender command instead')
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
        download_books(args.book_id, args.count, args.output)
    
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
        analyze_characters_command(
            args.input, args.output, args.model, args.provider,
            rate_limited=args.rate_limited, tokens_per_minute=args.tokens_per_minute
        )
    
    elif args.command == 'regender':
        # New unified command
        handle_regender_command(args)
    
    elif args.command == 'pipeline':
        pipeline(args.count, args.type, args.model)


if __name__ == "__main__":
    main()