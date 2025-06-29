#!/usr/bin/env python3
"""
regender-xyz - A CLI tool for transforming gender representation in literature
Version: 0.4.0
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

# Import our modules
from analyze_characters import analyze_text_file
from gender_transform import transform_text_file, TRANSFORM_TYPES
from utils import (
    get_openai_client, load_text_file, save_text_file,
    APIError, FileError, ReGenderError
)
from large_text_transform import transform_large_text

# Import book processing integration
try:
    from book_to_json import BookProcessorIntegration, process_book_to_json
    BOOK_PROCESSOR_AVAILABLE = True
except ImportError:
    BOOK_PROCESSOR_AVAILABLE = False

# Import interactive CLI module (if available)
try:
    from interactive_cli import interactive_transformation_setup
    INTERACTIVE_MODE_AVAILABLE = True
except ImportError:
    INTERACTIVE_MODE_AVAILABLE = False

# Import CLI visuals module (if available)
try:
    from cli_visuals import (
        print_fancy_banner, print_section_header, print_success, 
        print_warning, print_error, print_info, GenderSpinner,
        run_with_spinner, Colors
    )
    CLI_VISUALS_AVAILABLE = True
except ImportError:
    CLI_VISUALS_AVAILABLE = False

# Configuration
DEFAULT_MODEL = "gpt-4.1-mini"

def check_openai_api_key() -> bool:
    """Verify OpenAI API key is set and valid.
    
    Returns:
        bool: True if API key is valid, False otherwise
    """
    try:
        get_openai_client()
        return True
    except APIError as e:
        if CLI_VISUALS_AVAILABLE:
            print_error(f"Error: {e}")
            print_info("Please set your OpenAI API key with:")
            print(f"  {Colors.BRIGHT_GREEN}export OPENAI_API_KEY='your-api-key'{Colors.RESET}")
        else:
            print(f"Error: {e}")
            print("Please set your OpenAI API key with:")
            print("  export OPENAI_API_KEY='your-api-key'")
        return False

def print_banner():
    """Print application banner."""
    if CLI_VISUALS_AVAILABLE:
        print_fancy_banner()
    else:
        banner = """
╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  ⚡ regender-xyz ⚡                      
┃  ~ transforming gender in literature ~     
┃  [ Version 0.4.0 ]                      
┃                                           
┃  ✧ character analysis ✧ gender transformation ✧       
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        print(banner)

def preprocess_command(args) -> int:
    """Handle the preprocess command for cleaning books to JSON.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not BOOK_PROCESSOR_AVAILABLE:
        if CLI_VISUALS_AVAILABLE:
            print_error("Book preprocessing module not available")
        else:
            print("Error: Book preprocessing module not available")
        return 1
    
    try:
        if CLI_VISUALS_AVAILABLE:
            print_section_header("Book Preprocessing")
            print_info(f"Preprocessing book: {args.file}")
        else:
            print(f"Preprocessing book: {args.file}")
        
        # Check if input file exists
        if not os.path.exists(args.file):
            if CLI_VISUALS_AVAILABLE:
                print_error(f"Input file not found: {args.file}")
            else:
                print(f"Error: Input file not found: {args.file}")
            return 1
        
        # Set default output if not provided
        if not args.output:
            input_path = Path(args.file)
            args.output = str(input_path.parent / f"{input_path.stem}_clean.json")
        
        # Create processor
        processor = BookProcessorIntegration(verbose=not args.quiet)
        
        # Run preprocessing
        if CLI_VISUALS_AVAILABLE:
            def run_preprocessing():
                return processor.process_book_to_json(
                    args.file, 
                    args.output,
                    fix_long_sentences=not args.no_fix_sentences
                )
            
            book_data = run_with_spinner(
                run_preprocessing, 
                "Processing book to clean JSON format", 
                "neutral"
            )
        else:
            book_data = processor.process_book_to_json(
                args.file, 
                args.output,
                fix_long_sentences=not args.no_fix_sentences
            )
        
        # Optionally recreate text to verify
        if args.verify:
            if CLI_VISUALS_AVAILABLE:
                print_info("Verifying by recreating text from JSON...")
            else:
                print("Verifying by recreating text from JSON...")
            
            verify_file = args.output.replace('.json', '_recreated.txt')
            processor.recreate_text_from_json(args.output, verify_file)
            
            if CLI_VISUALS_AVAILABLE:
                print_success(f"Verification file saved to: {verify_file}")
            else:
                print(f"Verification file saved to: {verify_file}")
        
        if CLI_VISUALS_AVAILABLE:
            print_success(f"\nPreprocessing completed successfully!")
            print_info(f"Clean JSON saved to: {args.output}")
            print_info(f"Total chapters: {book_data['statistics']['total_chapters']}")
            print_info(f"Total sentences: {book_data['statistics']['total_sentences']:,}")
            print_info(f"Total words: {book_data['statistics']['total_words']:,}")
        else:
            print(f"\nPreprocessing completed successfully!")
            print(f"Clean JSON saved to: {args.output}")
            print(f"Total chapters: {book_data['statistics']['total_chapters']}")
            print(f"Total sentences: {book_data['statistics']['total_sentences']:,}")
            print(f"Total words: {book_data['statistics']['total_words']:,}")
        
        return 0
        
    except Exception as e:
        if CLI_VISUALS_AVAILABLE:
            print_error(f"Error during preprocessing: {e}")
        else:
            print(f"Error during preprocessing: {e}")
        return 1

def analyze_command(args) -> int:
    """Handle the analyze command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not check_openai_api_key():
        return 1
    
    try:
        if CLI_VISUALS_AVAILABLE:
            print_section_header(f"Character Analysis")
            print_info(f"Analyzing text file: {args.file}")
            
            # Run analysis with spinner
            def run_analysis():
                return analyze_text_file(args.file, args.output, args.model)
            
            run_with_spinner(run_analysis, "Analyzing text for characters", "neutral")
        else:
            print(f"Analyzing text file: {args.file}")
            analyze_text_file(args.file, args.output, args.model)
            
        return 0
    except ReGenderError as e:
        if CLI_VISUALS_AVAILABLE:
            print_error(f"Error: {e}")
        else:
            print(f"Error: {e}")
        return 1
    except Exception as e:
        if CLI_VISUALS_AVAILABLE:
            print_error(f"Unexpected error: {type(e).__name__}: {e}")
        else:
            print(f"Unexpected error: {type(e).__name__}: {e}")
        return 1

def transform_command(args) -> int:
    """Handle the transform command.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not check_openai_api_key():
        return 1
    
    try:
        transform_type = args.type
        transform_info = TRANSFORM_TYPES.get(transform_type, {})
        transform_name = transform_info.get('name', transform_type.capitalize())
        
        if CLI_VISUALS_AVAILABLE:
            print_section_header(f"{transform_name} Transformation")
            print_info(f"Transforming text file: {args.file}")
        else:
            print(f"Transforming text file: {args.file}")
        
        # Interactive mode setup
        options = {}
        if hasattr(args, 'interactive') and args.interactive and INTERACTIVE_MODE_AVAILABLE:
            if CLI_VISUALS_AVAILABLE:
                print_section_header("Interactive Mode")
            else:
                print("\n=== Interactive Mode Enabled ===")
                
            # If we have an analysis file from a previous step, use it
            analysis_file = None
            possible_analysis_files = [
                args.file.replace('.txt', '.analysis.json'),
                args.file.replace('.txt', '_analysis.json'),
                os.path.basename(args.file).replace('.txt', '.analysis.json'),
                os.path.basename(args.file).replace('.txt', '_analysis.json')
            ]
            
            for file_path in possible_analysis_files:
                if os.path.exists(file_path):
                    analysis_file = file_path
                    if CLI_VISUALS_AVAILABLE:
                        print_success(f"Found character analysis file: {analysis_file}")
                    else:
                        print(f"Found character analysis file: {analysis_file}")
                    break
            
            if not analysis_file:
                if CLI_VISUALS_AVAILABLE:
                    print_warning("No character analysis file found. Running in limited interactive mode.")
                else:
                    print("No character analysis file found. Running in limited interactive mode.")
            
            options = interactive_transformation_setup(analysis_file)
            if options:
                if CLI_VISUALS_AVAILABLE:
                    print_info("Applying custom options to transformation...")
                else:
                    print("\nApplying custom options to transformation...")
        
        # Run transformation with spinner if visuals available
        if CLI_VISUALS_AVAILABLE:
            def run_transform():
                return transform_text_file(args.file, args.type, args.output, args.model, **options)
            
            message = f"Applying {transform_name} transformation"
            run_with_spinner(run_transform, message, transform_type)
        else:
            transform_text_file(args.file, args.type, args.output, args.model, **options)
            
        return 0
    except ReGenderError as e:
        if CLI_VISUALS_AVAILABLE:
            print_error(f"Error: {e}")
        else:
            print(f"Error: {e}")
        return 1
    except Exception as e:
        if CLI_VISUALS_AVAILABLE:
            print_error(f"Unexpected error: {type(e).__name__}: {e}")
        else:
            print(f"Unexpected error: {type(e).__name__}: {e}")
        return 1

def novel_command(args) -> int:
    """Handle the novel command for processing full novels.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not check_openai_api_key():
        return 1
    
    try:
        transform_type = args.type
        transform_info = TRANSFORM_TYPES.get(transform_type, {})
        
        if not transform_info:
            if CLI_VISUALS_AVAILABLE:
                print_error(f"Invalid transformation type: {transform_type}")
            else:
                print(f"Error: Invalid transformation type: {transform_type}")
            return 1
        
        # Set default output path if not provided
        if not args.output:
            input_path = Path(args.file)
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            args.output = str(output_dir / f"{transform_type}_{input_path.stem}.txt")
        
        if CLI_VISUALS_AVAILABLE:
            print_section_header(f"Full Novel Transformation")
            print_info(f"Processing novel: {args.file}")
            print_info(f"Transformation type: {transform_info['name']}")
            print_info(f"Output file: {args.output}")
            print_info(f"Chapters per chunk: {args.chapters_per_chunk}")
            print_info(f"Debug directory: {args.debug_dir}")
            
            # Confirm before proceeding with full novel transformation
            if not args.yes:
                print(f"\n{Colors.BRIGHT_YELLOW}This operation will process the entire novel and may take a significant amount of time.{Colors.RESET}")
                confirm = input(f"Do you want to proceed? (y/n): ")
                if confirm.lower() not in ["y", "yes"]:
                    print_info("Operation cancelled by user")
                    return 0
            
            # Create debug directory if it doesn't exist
            debug_dir = Path(args.debug_dir)
            debug_dir.mkdir(exist_ok=True)
            
            # Run transformation with spinner
            def run_novel_transform():
                return transform_large_text(
                    args.file, 
                    transform_type, 
                    args.output, 
                    args.model,
                    args.chapters_per_chunk,
                    args.debug_dir
                )
            
            transformed_text, changes = run_with_spinner(
                run_novel_transform, 
                f"Transforming novel to {transform_info['name'].lower()}", 
                transform_type
            )
            
            print_success(f"\nNovel transformation completed successfully!")
            print_info(f"Made {len(changes)} changes")
            print_info(f"Transformed text saved to {args.output}")
            print_info(f"Debug files saved to {args.debug_dir}")
        else:
            print(f"Processing novel: {args.file}")
            print(f"Transformation type: {transform_info['name']}")
            print(f"Output file: {args.output}")
            
            # Confirm before proceeding with full novel transformation
            if not args.yes:
                print("\nThis operation will process the entire novel and may take a significant amount of time.")
                confirm = input("Do you want to proceed? (y/n): ")
                if confirm.lower() not in ["y", "yes"]:
                    print("Operation cancelled by user")
                    return 0
            
            # Create debug directory if it doesn't exist
            debug_dir = Path(args.debug_dir)
            debug_dir.mkdir(exist_ok=True)
            
            transformed_text, changes = transform_large_text(
                args.file, 
                transform_type, 
                args.output, 
                args.model,
                args.chapters_per_chunk,
                args.debug_dir
            )
            
            print(f"\nNovel transformation completed successfully!")
            print(f"Made {len(changes)} changes")
            print(f"Transformed text saved to {args.output}")
            print(f"Debug files saved to {args.debug_dir}")
        
        return 0
    except ReGenderError as e:
        if CLI_VISUALS_AVAILABLE:
            print_error(f"Error: {e}")
        else:
            print(f"Error: {e}")
        return 1
    except Exception as e:
        if CLI_VISUALS_AVAILABLE:
            print_error(f"Unexpected error: {type(e).__name__}: {e}")
        else:
            print(f"Unexpected error: {type(e).__name__}: {e}")
        return 1

def pipeline_command(args) -> int:
    """Handle the pipeline command (analyze then transform).
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    if not check_openai_api_key():
        return 1
    
    try:
        transform_type = args.type
        transform_info = TRANSFORM_TYPES.get(transform_type, {})
        transform_name = transform_info.get('name', transform_type.capitalize())
        
        if CLI_VISUALS_AVAILABLE:
            print_section_header("Full Pipeline")
            print_info(f"Running full pipeline on: {args.file}")
        else:
            print(f"Running full pipeline on: {args.file}")
        
        # First analyze the text
        if CLI_VISUALS_AVAILABLE:
            print_section_header("Step 1: Character Analysis")
        else:
            print("\n=== Step 1: Character Analysis ===")
            
        analysis_output = args.output.replace(".txt", ".analysis.json") if args.output else None
        
        # Run analysis with spinner if visuals available
        if CLI_VISUALS_AVAILABLE:
            def run_analysis():
                return analyze_text_file(args.file, analysis_output, args.model)
            
            analysis = run_with_spinner(run_analysis, "Analyzing text for characters", "neutral")
        else:
            analysis = analyze_text_file(args.file, analysis_output, args.model)
        
        # Then transform the text
        if CLI_VISUALS_AVAILABLE:
            print_section_header(f"Step 2: {transform_name} Transformation")
        else:
            print("\n=== Step 2: Gender Transformation ===")
        
        # Run transformation with spinner if visuals available
        if CLI_VISUALS_AVAILABLE:
            def run_transform():
                return transform_text_file(args.file, args.type, args.output, args.model)
            
            message = f"Applying {transform_name} transformation"
            run_with_spinner(run_transform, message, transform_type)
        else:
            transform_text_file(args.file, args.type, args.output, args.model)
        
        if CLI_VISUALS_AVAILABLE:
            print_success("\nPipeline completed successfully!")
        else:
            print("\nPipeline completed successfully!")
        return 0
    except ReGenderError as e:
        if CLI_VISUALS_AVAILABLE:
            print_error(f"Error: {e}")
        else:
            print(f"Error: {e}")
        return 1
    except Exception as e:
        if CLI_VISUALS_AVAILABLE:
            print_error(f"Unexpected error: {type(e).__name__}: {e}")
        else:
            print(f"Unexpected error: {type(e).__name__}: {e}")
        return 1

def main() -> int:
    """Main entry point for the CLI application.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    print_banner()
    
    # Create the top-level parser
    parser = argparse.ArgumentParser(
        description="Transform gender representation in literature",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Common arguments for all commands
    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"OpenAI model to use (default: {DEFAULT_MODEL})")
    common_args.add_argument("--no-cache", action="store_true", help="Disable caching of API responses")
    common_args.add_argument("-i", "--interactive", action="store_true", help="Enable interactive mode for customization")
    
    # Preprocess command
    if BOOK_PROCESSOR_AVAILABLE:
        preprocess_parser = subparsers.add_parser("preprocess", help="Preprocess a book to clean JSON format")
        preprocess_parser.add_argument("file", help="Path to the text file to preprocess")
        preprocess_parser.add_argument("-o", "--output", help="Path to save the JSON output")
        preprocess_parser.add_argument("--no-fix-sentences", action="store_true", 
                                     help="Skip fixing long sentences with embedded dialogues")
        preprocess_parser.add_argument("--verify", action="store_true", 
                                     help="Create a verification file by recreating text from JSON")
        preprocess_parser.add_argument("-q", "--quiet", action="store_true", 
                                     help="Suppress progress messages")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze characters in text", parents=[common_args])
    analyze_parser.add_argument("file", help="Path to the text file to analyze")
    analyze_parser.add_argument("-o", "--output", help="Path to save the analysis results")
    
    # Transform command
    transform_parser = subparsers.add_parser("transform", help="Transform gender in text", parents=[common_args])
    transform_parser.add_argument("file", help="Path to the text file to transform")
    transform_parser.add_argument(
        "-t", "--type", 
        choices=list(TRANSFORM_TYPES.keys()), 
        default="feminine",
        help="Type of transformation to apply"
    )
    transform_parser.add_argument("-o", "--output", help="Path to save the transformed text")
    
    # Pipeline command (analyze + transform)
    pipeline_parser = subparsers.add_parser("pipeline", help="Run full analysis and transformation pipeline", parents=[common_args])
    pipeline_parser.add_argument("file", help="Path to the text file to process")
    pipeline_parser.add_argument(
        "-t", "--type", 
        choices=list(TRANSFORM_TYPES.keys()), 
        default="feminine",
        help="Type of transformation to apply"
    )
    pipeline_parser.add_argument("-o", "--output", help="Path to save the transformed text")
    
    # Novel command (for processing full novels)
    novel_parser = subparsers.add_parser("novel", help="Process a full novel with chapter-based chunking", parents=[common_args])
    novel_parser.add_argument("file", help="Path to the novel file to process")
    novel_parser.add_argument(
        "-t", "--type", 
        choices=list(TRANSFORM_TYPES.keys()), 
        default="neutral",
        help="Type of transformation to apply"
    )
    novel_parser.add_argument("-o", "--output", help="Path to save the transformed novel")
    novel_parser.add_argument(
        "-c", "--chapters-per-chunk", 
        type=int, 
        default=5,
        help="Number of chapters to process in each chunk"
    )
    novel_parser.add_argument(
        "-d", "--debug-dir", 
        default="debug",
        help="Directory to save debug files"
    )
    novel_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt and proceed immediately"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle cache disabling if requested
    if hasattr(args, 'no_cache') and args.no_cache:
        try:
            # Instead of trying to rename directories, we'll set an environment variable
            # that our caching decorator can check to bypass the cache
            import os
            os.environ['REGENDER_DISABLE_CACHE'] = '1'
            print("Cache disabled for this run")
            
            # Register cleanup function to unset the environment variable at exit
            import atexit
            atexit.register(lambda: os.environ.pop('REGENDER_DISABLE_CACHE', None))
        except Exception as e:
            print(f"Warning: Could not disable cache: {e}")
    
    # Handle commands
    try:
        if args.command == "preprocess" and BOOK_PROCESSOR_AVAILABLE:
            return preprocess_command(args)
        elif args.command == "analyze":
            return analyze_command(args)
        elif args.command == "transform":
            return transform_command(args)
        elif args.command == "pipeline":
            return pipeline_command(args)
        elif args.command == "novel":
            return novel_command(args)
        else:
            parser.print_help()
            return 0
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130  # Standard exit code for SIGINT

if __name__ == "__main__":
    sys.exit(main())
