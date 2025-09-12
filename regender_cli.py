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
from src.models.character import Character, CharacterAnalysis, Gender
from src.models.transformation import TransformType
import json
import copy


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def interactive_character_selection(characters: CharacterAnalysis) -> dict:
    """
    Interactive character selection for custom transformations.
    
    Args:
        characters: Character analysis results
        
    Returns:
        Dictionary with custom character mappings
    """
    print("\n" + "="*60)
    print("🎭 INTERACTIVE CHARACTER SELECTION")
    print("="*60)
    
    print(f"\nFound {len(characters.characters)} characters in the book:")
    
    # Group characters by importance
    main_chars = [c for c in characters.characters if c.importance == "main"]
    supporting_chars = [c for c in characters.characters if c.importance == "supporting"]  
    minor_chars = [c for c in characters.characters if c.importance == "minor"]
    
    # Display characters
    all_chars = []
    idx = 1
    
    if main_chars:
        print(f"\n📚 MAIN CHARACTERS ({len(main_chars)}):")
        for char in main_chars:
            print(f"  {idx}. {char.name} ({char.gender.value})")
            all_chars.append(char)
            idx += 1
    
    if supporting_chars:
        print(f"\n👥 SUPPORTING CHARACTERS ({len(supporting_chars)}):")
        for char in supporting_chars:
            print(f"  {idx}. {char.name} ({char.gender.value})")
            all_chars.append(char)
            idx += 1
            
    if minor_chars:
        print(f"\n🎭 MINOR CHARACTERS ({len(minor_chars)}):")
        for char in minor_chars:
            print(f"  {idx}. {char.name} ({char.gender.value})")
            all_chars.append(char)
            idx += 1
    
    # Get user selections
    custom_mappings = {}
    
    print(f"\nSelect characters to transform (enter numbers separated by spaces, or 'all' for all characters):")
    print("Example: 1 3 5  or  all")
    
    try:
        sys.stdout.flush()  # Ensure prompt is displayed
        print("Your selection: ", end='', flush=True)
        selection = sys.stdin.readline().strip().lower()
        if not selection:
            print("No input received. Using 'all' as default.")
            selection = 'all'
    except EOFError:
        print("\nNo input received. Using 'all' as default.")
        selection = 'all'
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        return {}
    
    if selection == 'all':
        selected_chars = all_chars
    else:
        try:
            indices = [int(x) - 1 for x in selection.split()]
            selected_chars = [all_chars[i] for i in indices if 0 <= i < len(all_chars)]
        except (ValueError, IndexError):
            print("Invalid selection, using all characters.")
            selected_chars = all_chars
    
    print(f"\nConfiguring {len(selected_chars)} character(s):")
    
    for char in selected_chars:
        print(f"\n--- {char.name} (currently: {char.gender.value}) ---")
        
        # Get new gender
        print("Select new gender:")
        print("  1. male")
        print("  2. female") 
        print("  3. nonbinary")
        print("  4. keep unchanged")
        
        while True:
            try:
                sys.stdout.flush()
                choice = input("Enter choice (1-4): ").strip()
                if choice == '1':
                    new_gender = Gender.MALE
                    new_pronouns = {'subject': 'he', 'object': 'him', 'possessive': 'his'}
                    break
                elif choice == '2':
                    new_gender = Gender.FEMALE
                    new_pronouns = {'subject': 'she', 'object': 'her', 'possessive': 'her'}
                    break
                elif choice == '3':
                    new_gender = Gender.NONBINARY
                    new_pronouns = {'subject': 'they', 'object': 'them', 'possessive': 'their'}
                    break
                elif choice == '4':
                    new_gender = char.gender
                    new_pronouns = char.pronouns
                    break
                else:
                    print("Invalid choice, please enter 1-4.")
            except EOFError:
                print(f"\nNo input received. Keeping {char.name} unchanged.")
                new_gender = char.gender
                new_pronouns = char.pronouns
                break
            except KeyboardInterrupt:
                print("\nCancelled.")
                return {}
        
        # Ask for new name (optional)
        try:
            sys.stdout.flush()
            print(f"New name (press Enter to keep '{char.name}'): ", end='', flush=True)
            new_name_input = sys.stdin.readline().strip()
            new_name = new_name_input if new_name_input else char.name
        except EOFError:
            print(f"\nNo input received. Keeping name '{char.name}'.")
            new_name = char.name
        except KeyboardInterrupt:
            print("\nCancelled.")
            return {}
        
        # Store mapping
        custom_mappings[char.name] = {
            'original_gender': char.gender,
            'new_gender': new_gender,
            'original_name': char.name,
            'new_name': new_name,
            'pronouns': new_pronouns
        }
        
        # Also map aliases (create separate dict copies to avoid shared references)
        for alias in char.aliases:
            custom_mappings[alias] = {
                'original_gender': char.gender,
                'new_gender': new_gender,
                'original_name': char.name,
                'new_name': new_name,
                'pronouns': new_pronouns
            }
    
    print(f"\n✅ Configured {len(custom_mappings)} character mappings.")
    return custom_mappings


def apply_custom_transformation(app, book, characters, custom_mappings, output_path):
    """
    Apply custom character transformations to the book text.
    
    Args:
        app: Application instance
        book: Book object
        characters: CharacterAnalysis object
        custom_mappings: Dictionary of character transformations
        output_path: Output file path
        
    Returns:
        Result dictionary
    """
    print("Creating custom transformation rules...")
    
    # Create a simple text-based transformation for now
    # This is a minimal implementation to get text output working
    
    # Get the original book text - make a deep copy to avoid modifying original
    transformed_book = copy.deepcopy(book)
    
    # Apply simple text substitutions
    changes_made = 0
    
    # For each chapter, apply transformations
    for chapter_idx, chapter in enumerate(transformed_book.chapters):
        for para_idx, paragraph in enumerate(chapter.paragraphs):
            for sent_idx, sentence_text in enumerate(paragraph.sentences):
                original_text = sentence_text
                transformed_text = original_text
                
                # Apply character name and pronoun substitutions
                for char_name, mapping in custom_mappings.items():
                    if mapping['original_name'] != mapping['new_name']:
                        # Replace character names
                        transformed_text = transformed_text.replace(
                            mapping['original_name'], 
                            mapping['new_name']
                        )
                    
                    # Apply pronoun transformations based on gender change
                    if mapping['original_gender'] != mapping['new_gender']:
                        old_pronouns = get_pronouns_for_gender(mapping['original_gender'])
                        new_pronouns = mapping['pronouns']
                        
                        # Replace pronouns using word boundaries to avoid partial matches
                        import re
                        for old_pronoun, new_pronoun in zip_pronouns(old_pronouns, new_pronouns):
                            if old_pronoun and new_pronoun:
                                # Replace with word boundaries to avoid replacing parts of other words
                                pattern = r'\b' + re.escape(old_pronoun) + r'\b'
                                transformed_text = re.sub(pattern, new_pronoun, transformed_text, flags=re.IGNORECASE)
                                
                                # Handle capitalized versions at start of sentences
                                cap_pattern = r'\b' + re.escape(old_pronoun.capitalize()) + r'\b'
                                transformed_text = re.sub(cap_pattern, new_pronoun.capitalize(), transformed_text)
                
                if transformed_text != original_text:
                    paragraph.sentences[sent_idx] = transformed_text
                    changes_made += 1
    
    # Save the transformed book
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(transformed_book.to_dict(), f, indent=2, ensure_ascii=False)
    
    return {
        'success': True,
        'book_title': transformed_book.title,
        'characters': len(custom_mappings),
        'changes': changes_made,
        'output_path': str(output_path),
        'custom_mode': True
    }


def get_pronouns_for_gender(gender):
    """Get pronoun set for a gender."""
    if gender == Gender.MALE:
        return {'subject': 'he', 'object': 'him', 'possessive': 'his'}
    elif gender == Gender.FEMALE:
        return {'subject': 'she', 'object': 'her', 'possessive': 'her'}
    elif gender == Gender.NONBINARY:
        return {'subject': 'they', 'object': 'them', 'possessive': 'their'}
    else:
        return {}


def zip_pronouns(old_pronouns, new_pronouns):
    """Create pronoun replacement pairs."""
    pairs = []
    if 'subject' in old_pronouns and 'subject' in new_pronouns:
        pairs.append((old_pronouns['subject'], new_pronouns['subject']))
    if 'object' in old_pronouns and 'object' in new_pronouns:
        pairs.append((old_pronouns['object'], new_pronouns['object']))
    if 'possessive' in old_pronouns and 'possessive' in new_pronouns:
        pairs.append((old_pronouns['possessive'], new_pronouns['possessive']))
    return pairs


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
    elif args.transform_type == 'custom':
        # Interactive custom transformation
        print(f"Starting interactive character selection for {input_path}...")
        
        input_file = Path(input_path)
        
        # Check if we have a character analysis file already
        if input_file.suffix == '.json':
            # Look for existing character analysis file
            char_analysis_file = input_file.parent / f"{input_file.stem}-characters.json"
            
            if char_analysis_file.exists():
                print(f"Found existing character analysis: {char_analysis_file}")
                import json
                with open(char_analysis_file, 'r', encoding='utf-8') as f:
                    char_data = json.load(f)
                
                # Convert to CharacterAnalysis object
                characters = CharacterAnalysis.from_dict(char_data)
                
                # Load book data
                with open(input_path, 'r', encoding='utf-8') as f:
                    book_data = json.load(f)
                from src.models.book import Book
                book = Book.from_dict(book_data)
                
            else:
                print("Step 1: Analyzing characters...")
                characters_result = app.analyze_characters_sync(
                    file_path=input_path,
                    output_path=None  # Don't save, just get analysis
                )
                
                if not characters_result['success']:
                    print(f"❌ Error analyzing characters: {characters_result['error']}")
                    print("Tip: Try running character analysis first:")
                    print(f"  python regender_cli.py {input_path} character_analysis")
                    sys.exit(1)
                    
                # This would normally work but we have provider issues
                # For now, exit with helpful message
                print("❌ LLM provider not available. Please run character analysis first:")
                print(f"  python regender_cli.py {input_path} character_analysis")
                sys.exit(1)
        else:
            print("Error: Custom mode currently requires JSON input. Please convert to JSON first:")
            print(f"  python regender_cli.py {input_path} parse_only")
            sys.exit(1)
        
        # Run interactive selection
        print("\nStep 2: Interactive character selection...")
        custom_mappings = interactive_character_selection(characters)
        
        if not custom_mappings:
            print("No character mappings selected. Exiting.")
            sys.exit(0)
        
        # Apply custom transformation using the transform service
        if custom_mappings:
            print(f"\n🔧 Applying custom transformation with {len(custom_mappings)} character mappings:")
            for char_name, mapping in custom_mappings.items():
                if mapping['original_name'] != mapping['new_name'] or mapping['original_gender'] != mapping['new_gender']:
                    print(f"  • {mapping['original_name']} ({mapping['original_gender'].value}) → {mapping['new_name']} ({mapping['new_gender'].value})")
            
            # Create custom transformation using transform service
            print("\nStep 3: Applying transformations to text...")
            try:
                result = apply_custom_transformation(app, book, characters, custom_mappings, str(output_path))
            except Exception as e:
                print(f"❌ Error during transformation: {e}")
                result = {
                    'success': False,
                    'error': str(e),
                    'custom_mode': True
                }
        else:
            print("\n⚠️  No transformations to apply.")
            result = {
                'success': True,
                'book_title': book.title,
                'characters': 0,
                'changes': 0,
                'output_path': str(output_path),
                'custom_mode': True
            }
        
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
        elif result.get('custom_mode'):
            print(f"  Custom transformation configured")
            print(f"  Character mappings: {result['characters']}")
            print(f"  (Actual transformation not implemented yet)")
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
        nargs='?',  # Make optional
        choices=['all_male', 'all_female', 'gender_swap', 'nonbinary', 'custom', 'parse_only', 'character_analysis'],
        help='Type of transformation to apply (use parse_only for JSON, character_analysis for character detection, custom for interactive selection)'
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
    
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive character selection mode (automatically sets transform_type to custom)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle interactive mode
    if args.interactive:
        args.transform_type = 'custom'
    elif not args.transform_type:
        print("Error: transform_type is required unless using --interactive mode")
        parser.print_help()
        sys.exit(1)
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Process the book
    process_book(args)


if __name__ == '__main__':
    main()