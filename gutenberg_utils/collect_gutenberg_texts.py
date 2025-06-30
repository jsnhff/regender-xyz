#!/usr/bin/env python3
"""
Collect Gutenberg text files from individual folders into a single folder.

This script:
1. Scans the gutenberg_books directory for downloaded books
2. Copies pg####.txt files to a new folder
3. Renames them to pg####-Book_Title.txt for easy identification
"""

import os
import shutil
import re
from pathlib import Path
import argparse


def sanitize_filename(name: str, max_length: int = 50) -> str:
    """
    Sanitize a string for use in filename.
    
    Args:
        name: String to sanitize
        max_length: Maximum length for the name portion
        
    Returns:
        Sanitized string
    """
    # Remove/replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', '_', name)
    name = name.strip('._')
    
    # Limit length
    if len(name) > max_length:
        name = name[:max_length].rstrip('_')
    
    return name


def collect_gutenberg_texts(source_dir: str = "gutenberg_books", 
                          target_dir: str = "gutenberg_texts",
                          verbose: bool = True) -> int:
    """
    Collect all Gutenberg text files into a single directory.
    
    Args:
        source_dir: Directory containing the downloaded Gutenberg books
        target_dir: Directory to copy the text files to
        verbose: Whether to print progress messages
        
    Returns:
        Number of files copied
    """
    source_path = Path(source_dir)
    target_path = Path(target_dir)
    
    if not source_path.exists():
        print(f"Error: Source directory '{source_dir}' not found!")
        return 0
    
    # Create target directory
    target_path.mkdir(exist_ok=True)
    
    copied_count = 0
    skipped_count = 0
    
    # Scan for book folders
    book_folders = [f for f in source_path.iterdir() if f.is_dir()]
    
    if verbose:
        print(f"Found {len(book_folders)} book folders in {source_dir}")
        print(f"Copying text files to {target_dir}/")
        print("-" * 60)
    
    for folder in sorted(book_folders):
        # Extract book ID and title from folder name
        # Format: ####_Book_Title
        folder_name = folder.name
        match = re.match(r'^(\d+)_(.+)$', folder_name)
        
        if not match:
            if verbose:
                print(f"Skipping: {folder_name} (unexpected format)")
            skipped_count += 1
            continue
        
        book_id = match.group(1)
        book_title = match.group(2)
        
        # Look for the text file
        text_file = folder / f"pg{book_id}.txt"
        
        if not text_file.exists():
            # Try alternative naming
            alt_files = list(folder.glob("*.txt"))
            # Filter out metadata.txt
            alt_files = [f for f in alt_files if f.name != "metadata.txt"]
            
            if alt_files:
                text_file = alt_files[0]  # Take the first text file
            else:
                if verbose:
                    print(f"Skipping: {folder_name} (no text file found)")
                skipped_count += 1
                continue
        
        # Create new filename
        safe_title = sanitize_filename(book_title)
        new_filename = f"pg{book_id}-{safe_title}.txt"
        target_file = target_path / new_filename
        
        # Copy the file
        try:
            shutil.copy2(text_file, target_file)
            copied_count += 1
            
            if verbose:
                # Get file size
                size_kb = text_file.stat().st_size / 1024
                print(f"Copied: {new_filename} ({size_kb:.1f} KB)")
                
        except Exception as e:
            print(f"Error copying {text_file}: {e}")
            skipped_count += 1
    
    if verbose:
        print("-" * 60)
        print(f"Summary:")
        print(f"  Files copied: {copied_count}")
        print(f"  Folders skipped: {skipped_count}")
        print(f"  Total size: {sum(f.stat().st_size for f in target_path.glob('*.txt')) / (1024*1024):.1f} MB")
    
    return copied_count


def list_collected_texts(target_dir: str = "gutenberg_texts"):
    """List all collected text files with their details."""
    target_path = Path(target_dir)
    
    if not target_path.exists():
        print(f"Directory '{target_dir}' not found!")
        return
    
    files = sorted(target_path.glob("pg*.txt"))
    
    print(f"\nCollected texts in {target_dir}:")
    print("-" * 80)
    print(f"{'ID':<8} {'Title':<50} {'Size (KB)':<10}")
    print("-" * 80)
    
    for file in files:
        # Extract ID and title from filename
        match = re.match(r'^pg(\d+)-(.+)\.txt$', file.name)
        if match:
            book_id = match.group(1)
            title = match.group(2).replace('_', ' ')
            size_kb = file.stat().st_size / 1024
            
            # Truncate title if too long
            if len(title) > 47:
                title = title[:47] + "..."
            
            print(f"{book_id:<8} {title:<50} {size_kb:>8.1f}")
    
    print("-" * 80)
    print(f"Total: {len(files)} files, {sum(f.stat().st_size for f in files) / (1024*1024):.1f} MB")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect Gutenberg text files into a single directory"
    )
    parser.add_argument(
        "-s", "--source",
        default="gutenberg_books",
        help="Source directory containing downloaded books (default: gutenberg_books)"
    )
    parser.add_argument(
        "-t", "--target",
        default="gutenberg_texts",
        help="Target directory for collected texts (default: gutenberg_texts)"
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List collected texts after copying"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress messages"
    )
    
    args = parser.parse_args()
    
    # Collect the texts
    count = collect_gutenberg_texts(
        source_dir=args.source,
        target_dir=args.target,
        verbose=not args.quiet
    )
    
    # Optionally list the results
    if args.list and count > 0:
        list_collected_texts(args.target)


if __name__ == "__main__":
    main()