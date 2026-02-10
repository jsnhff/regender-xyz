#!/usr/bin/env python3
"""
Regender CLI - Transform gender representation in literature

This CLI uses the modern service-oriented architecture to process books,
analyze characters, and apply gender transformations.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Add src to path for new architecture
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import Application
from src.cli import AppDisplay, CLIDisplay, QuietDisplay, VerboseDisplay, run_interactive
from src.cli.tui import run_tui


def setup_logging(verbose: bool = False, quiet: bool = False, tui: bool = False):
    """Set up logging configuration."""
    if tui:
        # TUI mode: suppress ALL logging to keep display clean
        level = logging.CRITICAL + 1  # Above CRITICAL = nothing
    elif quiet:
        # Only show critical errors in quiet mode
        level = logging.CRITICAL
    elif verbose:
        # Show debug output in verbose mode
        level = logging.DEBUG
    else:
        # In normal mode, suppress most logging (clean CLI experience)
        level = logging.CRITICAL

    logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Also suppress all existing loggers
    if tui or quiet:
        for name in logging.root.manager.loggerDict:
            logging.getLogger(name).setLevel(level)


def get_display(verbose: bool, quiet: bool):
    """Get the appropriate display based on flags."""
    if quiet:
        return QuietDisplay()
    elif verbose:
        return VerboseDisplay()
    else:
        return CLIDisplay()


def get_output_path(args) -> Path:
    """Generate output path based on input and transform type."""
    if getattr(args, "output", None):
        return Path(args.output)

    input_file = Path(args.input)

    # Extract book name and create folder name
    book_name = input_file.stem
    # Remove common prefixes like pg12- or pg43-
    if book_name.startswith("pg") and "-" in book_name:
        book_name = book_name.split("-", 1)[1]
    # Convert to lowercase and replace spaces/underscores with hyphens
    book_folder = book_name.lower().replace("_", "-").replace(" ", "-")

    if args.transform_type == "parse_only":
        # For parsing: keep in books/json/ with same name
        if "texts" in str(input_file.parent):
            output_dir = Path(str(input_file.parent).replace("texts", "json"))
        else:
            output_dir = input_file.parent
        return output_dir / f"{input_file.stem}.json"
    elif args.transform_type == "character_analysis":
        # For character analysis: save to book's output folder
        output_dir = Path("books/output") / book_folder
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / "characters.json"
    else:
        # For transformations: save to book's output folder with transformation type
        output_dir = Path("books/output") / book_folder
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{args.transform_type}.json"


def process_book_with_display(args, display):
    """Process book transformation with rich display."""
    # Initialize application
    config_path = getattr(args, "config", None) or "src/config.json"
    app = Application(config_path)

    input_path = args.input
    output_path = get_output_path(args)

    # Extract book name for header
    input_file = Path(input_path)
    book_name = input_file.stem
    if book_name.startswith("pg") and "-" in book_name:
        book_name = book_name.split("-", 1)[1]

    # Show header
    display.show_header(book_name)

    # Process selected characters if specified
    selected_characters = None
    if getattr(args, "characters", None):
        selected_characters = [name.strip() for name in args.characters.split(",")]
    elif getattr(args, "characters_file", None):
        with open(args.characters_file) as f:
            selected_characters = [line.strip() for line in f if line.strip()]

    # Create progress context from display
    progress_context = display.create_progress_context()

    # Process with progress reporting
    no_qc = getattr(args, "no_qc", False)
    result = app.process_book_with_progress_sync(
        file_path=input_path,
        transform_type=args.transform_type,
        progress_context=progress_context,
        output_path=str(output_path),
        quality_control=not no_qc,
        selected_characters=selected_characters,
    )

    # Show results
    if result["success"]:
        display.show_summary(
            elapsed_seconds=result.get("elapsed_seconds", 0),
            api_calls=result.get("api_calls", 0),
            tokens=result.get("total_tokens", 0),
            output_path=str(output_path),
        )
    else:
        display.show_error(result["error"])
        app.shutdown()
        sys.exit(1)

    # Clean up
    app.shutdown()


def process_book_with_app_display(args, display: AppDisplay = None):
    """Process book using AppDisplay with split-screen layout maintained throughout."""
    # Initialize application
    config_path = getattr(args, "config", None) or "src/config.json"
    app = Application(config_path)

    input_path = args.input
    output_path = get_output_path(args)

    # Use provided display or create new one
    if display is None:
        # Extract book name
        input_file = Path(input_path)
        book_name = input_file.stem
        if book_name.startswith("pg") and "-" in book_name:
            book_name = book_name.split("-", 1)[1]
        book_title = book_name.replace("_", " ").replace("-", " ").title()

        display = AppDisplay()
        display.clear()
        display.set_book(book_title)
        display.set_transform(args.transform_type)

    # Start processing
    display.start_processing()

    # Start live display
    display.start_live()

    # Process selected characters if specified
    selected_characters = None
    if getattr(args, "characters", None):
        selected_characters = [name.strip() for name in args.characters.split(",")]
    elif getattr(args, "characters_file", None):
        with open(args.characters_file) as f:
            selected_characters = [line.strip() for line in f if line.strip()]

    # Create progress context from display
    progress_context = display.create_progress_context()

    # Process with progress reporting
    no_qc = getattr(args, "no_qc", False)
    try:
        result = app.process_book_with_progress_sync(
            file_path=input_path,
            transform_type=args.transform_type,
            progress_context=progress_context,
            output_path=str(output_path),
            quality_control=not no_qc,
            selected_characters=selected_characters,
        )

        # Update display with results
        if result["success"]:
            display.set_complete(str(output_path))
        else:
            display.set_error(result["error"])
    except Exception as e:
        display.set_error(str(e))
        result = {"success": False, "error": str(e)}

    # Stop live and show final state
    display.show_final()

    # Exit with error if failed
    if not result["success"]:
        app.shutdown()
        sys.exit(1)

    # Clean up
    app.shutdown()


def process_book_legacy(args):
    """Process book using legacy output (for parse_only and character_analysis)."""
    # Initialize application
    config_path = getattr(args, "config", None) or "src/config.json"
    app = Application(config_path)

    input_path = args.input
    output_path = get_output_path(args)

    # Check mode
    if args.transform_type == "parse_only":
        print(f"Parsing {input_path} to canonical JSON format...")
        result = app.parse_book_sync(file_path=input_path, output_path=str(output_path))
    elif args.transform_type == "character_analysis":
        print(f"Analyzing characters in {input_path}...")
        result = app.analyze_characters_sync(file_path=input_path, output_path=str(output_path))
    else:
        # Should not reach here
        print("Error: Unexpected transform type for legacy processing")
        sys.exit(1)

    # Display results
    if result["success"]:
        print("\n✅ Success!")
        print(f"  Book: {result['book_title']}")
        if args.transform_type == "parse_only":
            print(f"  Chapters: {result.get('chapters', 'N/A')}")
            print(f"  Paragraphs: {result.get('paragraphs', 'N/A')}")
            print(f"  Sentences: {result.get('sentences', 'N/A')}")
        elif args.transform_type == "character_analysis":
            print(f"  Total characters: {result.get('total_characters', 0)}")
            print(f"  By gender: {result.get('by_gender', {})}")
            print(f"  By importance: {result.get('by_importance', {})}")
            if result.get("main_characters"):
                print(f"  Main characters: {', '.join(result['main_characters'][:5])}")
        print(f"  Output: {result['output_path']}")
    else:
        print(f"\n❌ Error: {result['error']}")
        app.shutdown()
        sys.exit(1)

    # Clean up
    app.shutdown()


def process_book(args):
    """Process book - route to appropriate handler based on transform type."""
    # Get display based on flags
    verbose = getattr(args, "verbose", False)
    quiet = getattr(args, "quiet", False)
    display = get_display(verbose, quiet)

    # For parse_only and character_analysis, use legacy output
    if args.transform_type in ["parse_only", "character_analysis"]:
        process_book_legacy(args)
    else:
        # For transformations, use rich display
        process_book_with_display(args, display)


class Args:
    """Simple namespace for holding arguments."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Regender-XYZ CLI - Transform gender representation in literature"
    )

    # Main arguments (optional - if not provided, launch interactive mode)
    parser.add_argument("input", nargs="?", help="Input file path (text or JSON)")

    parser.add_argument(
        "transform_type",
        nargs="?",
        choices=[
            "all_male",
            "all_female",
            "gender_swap",
            "nonbinary",
            "parse_only",
            "character_analysis",
        ],
        help="Type of transformation to apply",
    )

    parser.add_argument(
        "-o", "--output", help="Output file path (defaults to input_name_transform_type.json)"
    )

    # Configuration options
    parser.add_argument("--config", help="Path to configuration file (default: src/config.json)")

    parser.add_argument("--no-qc", action="store_true", help="Skip quality control")

    # Verbosity options (mutually exclusive)
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    verbosity_group.add_argument(
        "-q", "--quiet", action="store_true", help="Quiet mode - only output file path on success"
    )

    # Selective transformation options
    parser.add_argument(
        "--characters",
        help="Comma-separated list of character names to transform (e.g., 'Dr. Jekyll,Mr. Hyde')",
    )

    parser.add_argument(
        "--characters-file",
        help="Path to file containing character names to transform (one per line)",
    )

    # Parse arguments
    args = parser.parse_args()

    # If no input provided, launch interactive TUI mode
    if args.input is None:
        # Suppress ALL logging for clean TUI
        setup_logging(tui=True)

        # Create processing callback for TUI
        def process_callback(input_path, transform_type, no_qc, progress_callback, stage_callback):
            """Process book within TUI context."""
            from src.progress import ProgressContext

            config_path = "src/config.json"
            app = Application(config_path)

            # Calculate output path
            input_file = Path(input_path)
            book_name = input_file.stem
            if book_name.startswith("pg") and "-" in book_name:
                book_name = book_name.split("-", 1)[1]
            book_folder = book_name.lower().replace("_", "-").replace(" ", "-")

            if transform_type == "parse_only":
                if "texts" in str(input_file.parent):
                    output_dir = Path(str(input_file.parent).replace("texts", "json"))
                else:
                    output_dir = input_file.parent
                output_path = output_dir / f"{input_file.stem}.json"
            elif transform_type == "character_analysis":
                output_dir = Path("books/output") / book_folder
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / "characters.json"
            else:
                output_dir = Path("books/output") / book_folder
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{transform_type}.json"

            # Create progress context
            progress_context = ProgressContext(
                on_progress=progress_callback,
                on_stage_complete=stage_callback,
            )

            # Run the transformation
            result = app.process_book_with_progress_sync(
                file_path=input_path,
                transform_type=transform_type,
                progress_context=progress_context,
                output_path=str(output_path),
                quality_control=not no_qc,
            )

            app.shutdown()

            return {
                "success": result.get("success", False),
                "output_path": str(output_path) if result.get("success") else None,
                "error": result.get("error"),
            }

        # Run the full TUI with processing
        result = run_tui(process_callback=process_callback)
        if result is None:
            sys.exit(0)
        return

    # Validate that we have required arguments
    if args.transform_type is None:
        parser.error("transform_type is required when input is provided")

    # Set up logging
    setup_logging(args.verbose, args.quiet)

    # Process the book
    process_book(args)


if __name__ == "__main__":
    main()
