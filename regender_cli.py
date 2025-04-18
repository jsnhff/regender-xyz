#!/usr/bin/env python3
"""
regender-xyz - A CLI tool for transforming gender representation in literature
Version: 0.3.0
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
        print(f"Error: {e}")
        print("Please set your OpenAI API key with:")
        print("  export OPENAI_API_KEY='your-api-key'")
        return False

def print_banner():
    """Print application banner."""
    banner = """
╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┃  ⚡ regender-xyz ⚡                      
┃  ~ transforming gender in literature ~     
┃  [ Version 0.3.0 ]                      
┃                                           
┃  ✧ character analysis ✧ gender transformation ✧       
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    print(banner)

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
        print(f"Analyzing text file: {args.file}")
        analyze_text_file(args.file, args.output, args.model)
        return 0
    except ReGenderError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
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
        print(f"Transforming text file: {args.file}")
        transform_text_file(args.file, args.type, args.output, args.model)
        return 0
    except ReGenderError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
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
        print(f"Running full pipeline on: {args.file}")
        
        # First analyze the text
        print("\n=== Step 1: Character Analysis ===")
        analysis_output = args.output.replace(".txt", ".analysis.json") if args.output else None
        analysis = analyze_text_file(args.file, analysis_output, args.model)
        
        # Then transform the text
        print("\n=== Step 2: Gender Transformation ===")
        transform_text_file(args.file, args.type, args.output, args.model)
        
        print("\nPipeline completed successfully!")
        return 0
    except ReGenderError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
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
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle cache disabling if requested
    if hasattr(args, 'no_cache') and args.no_cache:
        try:
            import os
            cache_dir = Path(".cache")
            if cache_dir.exists():
                temp_cache_dir = Path(".cache_disabled")
                os.rename(cache_dir, temp_cache_dir)
                # Register cleanup function to restore cache directory
                import atexit
                atexit.register(lambda: os.rename(temp_cache_dir, cache_dir) if temp_cache_dir.exists() else None)
        except Exception as e:
            print(f"Warning: Could not disable cache: {e}")
    
    # Handle commands
    try:
        if args.command == "analyze":
            return analyze_command(args)
        elif args.command == "transform":
            return transform_command(args)
        elif args.command == "pipeline":
            return pipeline_command(args)
        else:
            parser.print_help()
            return 0
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130  # Standard exit code for SIGINT

if __name__ == "__main__":
    sys.exit(main())
