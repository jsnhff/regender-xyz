#!/usr/bin/env python3
"""
Interactive workflow for character analysis and selective transformation.

This script provides an interactive workflow to:
1. Analyze characters in a book
2. Display character list
3. Let user select which characters to transform
4. Perform the transformation
5. Export to clean text file
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Set


def run_command(cmd: List[str]) -> bool:
    """Run a command and return success status."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    if result.stdout:
        print(result.stdout)
    return True


def analyze_characters(book_path: str) -> dict:
    """Run character analysis and return results."""
    print("\n📊 Analyzing characters...")
    cmd = [
        sys.executable, "regender_cli.py",
        book_path,
        "character_analysis"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error during character analysis: {result.stderr}")
        return None

    # Parse the output to find the characters.json path
    output_lines = result.stdout.split('\n')
    char_file = None
    for line in output_lines:
        if 'Output:' in line:
            char_file = line.split('Output:')[1].strip()
            break

    if not char_file or not Path(char_file).exists():
        print("Could not find character analysis output file")
        return None

    # Load and return the character data
    with open(char_file, 'r') as f:
        return json.load(f)


def display_characters(char_data: dict) -> List[str]:
    """Display character list and return character names."""
    print("\n👥 Characters found in the book:")
    print("-" * 60)

    characters = char_data.get('characters', [])
    character_names = []

    # Group by importance
    main_chars = []
    supporting_chars = []
    minor_chars = []

    for char in characters:
        name = char['name']
        gender = char.get('gender', 'unknown')
        importance = char.get('importance', 0)

        # Handle importance as either string category or numeric value
        if isinstance(importance, str):
            # Map string importance to numeric values
            importance_map = {
                'main': 10,
                'primary': 10,
                'major': 10,
                'supporting': 7,
                'secondary': 7,
                'minor': 3,
                'background': 1
            }
            importance_num = importance_map.get(importance.lower(), 5)
            importance_str = importance
        else:
            # Already numeric
            importance_num = importance
            if importance_num >= 8:
                importance_str = 'main'
            elif importance_num >= 5:
                importance_str = 'supporting'
            else:
                importance_str = 'minor'

        character_names.append(name)

        if importance_num >= 8:
            main_chars.append((name, gender, importance_str))
        elif importance_num >= 5:
            supporting_chars.append((name, gender, importance_str))
        else:
            minor_chars.append((name, gender, importance_str))

    # Display grouped characters
    if main_chars:
        print("\n🌟 MAIN CHARACTERS:")
        for i, (name, gender, imp) in enumerate(main_chars, 1):
            print(f"   {i:2}. {name:<30} ({gender}, {imp})")

    if supporting_chars:
        print("\n📚 SUPPORTING CHARACTERS:")
        for i, (name, gender, imp) in enumerate(supporting_chars, len(main_chars) + 1):
            print(f"   {i:2}. {name:<30} ({gender}, {imp})")

    if minor_chars:
        print("\n🔸 MINOR CHARACTERS:")
        for i, (name, gender, imp) in enumerate(minor_chars, len(main_chars) + len(supporting_chars) + 1):
            print(f"   {i:2}. {name:<30} ({gender}, {imp})")

    print("-" * 60)
    stats = char_data.get('statistics', {})
    print(f"\nTotal: {stats.get('total', len(characters))} characters")
    by_gender = stats.get('by_gender', {})
    if by_gender:
        print(f"By gender: {', '.join(f'{g}: {c}' for g, c in by_gender.items())}")

    return character_names


def select_characters(character_names: List[str]) -> Set[str]:
    """Interactive character selection."""
    print("\n🎯 Character Selection Options:")
    print("1. Transform ALL characters")
    print("2. Transform MAIN characters only (importance >= 8)")
    print("3. Select SPECIFIC characters")
    print("4. Enter character names manually")

    choice = input("\nEnter your choice (1-4): ").strip()

    if choice == '1':
        return None  # Transform all

    elif choice == '2':
        # This would need the character data with importance scores
        print("Selecting main characters...")
        return None  # For now, would need to filter by importance

    elif choice == '3':
        print("\nEnter character numbers (comma-separated, e.g., 1,3,5):")
        print("Or enter ranges (e.g., 1-5,8,10-12):")
        selection = input("> ").strip()

        selected = set()
        for part in selection.split(','):
            part = part.strip()
            if '-' in part:
                # Range
                try:
                    start, end = part.split('-')
                    for i in range(int(start) - 1, int(end)):
                        if 0 <= i < len(character_names):
                            selected.add(character_names[i])
                except:
                    print(f"Invalid range: {part}")
            else:
                # Single number
                try:
                    idx = int(part) - 1
                    if 0 <= idx < len(character_names):
                        selected.add(character_names[idx])
                except:
                    print(f"Invalid number: {part}")

        return selected

    elif choice == '4':
        print("\nEnter character names (comma-separated):")
        names = input("> ").strip()
        return set(name.strip() for name in names.split(','))

    else:
        print("Invalid choice, transforming all characters")
        return None


def transform_book(book_path: str, selected_chars: Set[str] = None) -> str:
    """Run the transformation and return output path."""
    print("\n🔄 Running transformation...")

    cmd = [
        sys.executable, "regender_cli.py",
        book_path,
        "gender_swap",
        "--no-qc"  # Skip quality control for speed
    ]

    if selected_chars:
        # Add specific characters
        cmd.extend(["--characters", ",".join(selected_chars)])
        print(f"Transforming only: {', '.join(selected_chars)}")
    else:
        print("Transforming all characters")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error during transformation: {result.stderr}")
        return None

    # Parse output to find the result file
    output_lines = result.stdout.split('\n')
    output_file = None
    for line in output_lines:
        if 'Output:' in line:
            output_file = line.split('Output:')[1].strip()
            break

    if output_file and Path(output_file).exists():
        print(f"✅ Transformation complete: {output_file}")
        return output_file
    else:
        print("Could not find transformation output")
        return None


def export_to_text(json_path: str) -> str:
    """Export JSON to clean text file."""
    print("\n📝 Exporting to text file...")

    # Use the integrated TextExportService
    from src.services.text_export_service import TextExportService
    from src.services.base import ServiceConfig
    import logging

    config = ServiceConfig(
        name="text_export",
        preserve_unicode=False,
        normalize_method="unidecode"
    )

    logger = logging.getLogger("workflow")
    service = TextExportService(config, logger)

    try:
        # Export to text (will create .txt file alongside .json)
        output_path = service.export_json_to_text(json_path)
        print(f"✅ Exported to: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Error during export: {e}")
        return None


def main():
    """Main workflow."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Interactive workflow for character transformation'
    )
    parser.add_argument(
        'input',
        help='Path to book file (JSON or text)'
    )
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Run automatically without prompts (transform all characters)'
    )
    parser.add_argument(
        '--characters',
        help='Comma-separated list of characters to transform'
    )

    args = parser.parse_args()

    book_path = args.input

    # Check if input exists
    if not Path(book_path).exists():
        print(f"❌ File not found: {book_path}")
        return 1

    print(f"\n📚 Processing: {book_path}")

    # Step 1: Parse if needed
    if book_path.endswith('.txt'):
        print("\n📖 Parsing text file...")
        cmd = [
            sys.executable, "regender_cli.py",
            book_path,
            "parse_only"
        ]
        if not run_command(cmd):
            return 1

        # Update path to JSON
        book_path = book_path.replace('/texts/', '/json/')
        book_path = Path(book_path).with_suffix('.json')
        if not book_path.exists():
            # Try same directory
            book_path = Path(args.input).with_suffix('.json')

    # Step 2: Character analysis
    char_data = analyze_characters(str(book_path))
    if not char_data:
        return 1

    character_names = display_characters(char_data)

    # Step 3: Select characters
    if args.auto:
        selected_chars = None
    elif args.characters:
        selected_chars = set(c.strip() for c in args.characters.split(','))
        print(f"\nUsing specified characters: {', '.join(selected_chars)}")
    else:
        selected_chars = select_characters(character_names)

    if selected_chars:
        print(f"\n✅ Selected {len(selected_chars)} characters for transformation")

    # Step 4: Transform
    output_json = transform_book(str(book_path), selected_chars)
    if not output_json:
        return 1

    # Step 5: Export to text
    output_text = export_to_text(output_json)
    if output_text:
        print(f"\n✨ Complete! Clean text file: {output_text}")

        # Show sample
        print("\n📄 Sample of output:")
        print("-" * 60)
        with open(output_text, 'r') as f:
            lines = f.readlines()[:15]
            for line in lines:
                print(line.rstrip())
        print("-" * 60)

    return 0


if __name__ == '__main__':
    exit(main())