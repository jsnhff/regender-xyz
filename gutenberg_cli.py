#!/usr/bin/env python3
"""
Simple Gutenberg CLI - Download and process Project Gutenberg books with minimal hassle

Usage:
    python gutenberg.py download              # Download top 100 books
    python gutenberg.py download --count 50   # Download top 50 books
    python gutenberg.py process               # Convert all to JSON
    python gutenberg.py pipeline              # Download and process
    python gutenberg.py list                  # List downloaded books
"""

import argparse
import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent))

from gutenberg_utils.download_gutenberg_books import GutenbergDownloader
from gutenberg_utils.collect_gutenberg_texts import collect_gutenberg_texts, list_collected_texts
from gutenberg_utils.process_all_gutenberg import process_all_books


def download_books(count=100, output_dir="gutenberg_books"):
    """Download top books from Project Gutenberg"""
    print(f"📚 Downloading top {count} books from Project Gutenberg...")
    print("=" * 70)
    
    downloader = GutenbergDownloader(output_dir=output_dir, max_books=count)
    stats = downloader.download_top_books()
    
    print("\n" + "=" * 70)
    print("✅ Download Complete!")
    print(f"📊 Downloaded: {stats['successful']} books")
    print(f"❌ Failed: {stats['failed']} books")
    print(f"💾 Total size: {stats['total_size']}")
    
    # Automatically collect texts
    print("\n📂 Collecting text files...")
    collect_stats = collect_gutenberg_texts(
        input_dir=output_dir,
        output_dir="gutenberg_texts"
    )
    print(f"✅ Collected {collect_stats['collected']} text files")
    
    return stats


def process_books(input_dir="gutenberg_texts", output_dir="gutenberg_json"):
    """Process all downloaded books to JSON format"""
    print("🔄 Processing books to JSON format...")
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


def pipeline(count=100):
    """Run the complete pipeline: download and process"""
    print("🚀 Running complete Gutenberg pipeline...")
    print("=" * 70)
    
    # Download
    download_stats = download_books(count)
    
    # Process
    if download_stats['successful'] > 0:
        print("\n" + "=" * 70)
        process_stats = process_books()
        
        print("\n" + "=" * 70)
        print("🎉 Pipeline Complete!")
        print(f"📚 Books ready for processing in: gutenberg_json/")
    else:
        print("❌ No books downloaded, skipping processing")


def list_books():
    """List all collected books"""
    list_collected_texts("gutenberg_texts")
    print("\n💡 Tip: Use 'python regender_cli.py preprocess gutenberg_texts/[filename]' to process individual books")


def main():
    parser = argparse.ArgumentParser(
        description="Simple Gutenberg CLI - Download and process Project Gutenberg books",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python gutenberg.py download              # Download top 100 books
  python gutenberg.py download --count 50   # Download top 50 books  
  python gutenberg.py process               # Convert all to JSON
  python gutenberg.py pipeline              # Download and process
  python gutenberg.py list                  # List downloaded books
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download books from Project Gutenberg')
    download_parser.add_argument('--count', type=int, default=100, help='Number of books to download (default: 100)')
    download_parser.add_argument('--output', default='gutenberg_books', help='Output directory')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process downloaded books to JSON')
    process_parser.add_argument('--input', default='gutenberg_texts', help='Input directory')
    process_parser.add_argument('--output', default='gutenberg_json', help='Output directory')
    
    # Pipeline command
    pipeline_parser = subparsers.add_parser('pipeline', help='Download and process books')
    pipeline_parser.add_argument('--count', type=int, default=100, help='Number of books to download')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List downloaded books')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'download':
        download_books(args.count, args.output)
    elif args.command == 'process':
        process_books(args.input, args.output)
    elif args.command == 'pipeline':
        pipeline(args.count)
    elif args.command == 'list':
        list_books()


if __name__ == "__main__":
    main()