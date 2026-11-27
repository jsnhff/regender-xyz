#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Jason Huff
"""
Regender CLI - Transform gender representation in literature

This CLI uses the modern service-oriented architecture to process books,
analyze characters, and apply gender transformations.

Copyright (C) 2026 Jason Huff

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option)
any later version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

# Add src to path for new architecture
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.app import Application, run_problems  # noqa: E402


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


async def process_book(args):
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

        # Extract book name and create folder name with timestamp
        book_name = input_file.stem
        # Remove common prefixes like pg12- or pg43-
        if book_name.startswith("pg") and "-" in book_name:
            book_name = book_name.split("-", 1)[1]
        # Convert to lowercase and replace spaces/underscores with hyphens
        book_base = book_name.lower().replace("_", "-").replace(" ", "-")
        # Add timestamp to folder name (YYYYMMDD-HHMMSS format)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        book_folder = f"{book_base}-{timestamp}"

        if args.transform_type == "parse_only":
            # For parsing: keep in books/json/ with same name
            if "texts" in str(input_file.parent):
                output_dir = Path(str(input_file.parent).replace("texts", "json"))
            else:
                output_dir = input_file.parent
            output_path = output_dir / f"{input_file.stem}.json"
        elif args.transform_type == "character_analysis":
            # For character analysis: save to book's output folder
            output_dir = Path("books/output") / book_folder
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / "characters.json"
        else:
            # For transformations: save to book's output folder with transformation type
            output_dir = Path("books/output") / book_folder
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{args.transform_type}.json"

    # Check mode
    if args.transform_type == "parse_only":
        print(f"Parsing {input_path} to canonical JSON format...")
        # Await directly: the _sync wrappers spin a nested event loop, which
        # raises inside async_main's running loop.
        result = await app.parse_book(file_path=input_path, output_path=str(output_path))
    elif args.transform_type == "character_analysis":
        print(f"Analyzing characters in {input_path}...")
        result = await app.analyze_characters(file_path=input_path, output_path=str(output_path))
    else:
        # Process selected characters if specified
        selected_characters = None
        if args.characters:
            # Parse comma-separated list
            selected_characters = [name.strip() for name in args.characters.split(",")]
            print(f"  Selective transformation for: {', '.join(selected_characters)}")
        elif args.characters_file:
            # Read from file
            with open(args.characters_file) as f:
                selected_characters = [line.strip() for line in f if line.strip()]
            print(f"  Selective transformation for {len(selected_characters)} characters from file")

        # Parse name map if provided
        name_map = None
        if args.name_map:
            p = Path(args.name_map.strip())
            name_map = json.loads(p.read_text() if p.is_file() else args.name_map)
            print(f"  Name substitutions: {', '.join(f'{k}→{v}' for k, v in name_map.items())}")

        # Process the book with transformation
        print(f"Processing {input_path} with {args.transform_type} transformation...")
        result = await app.process_book(
            file_path=input_path,
            transform_type=args.transform_type,
            output_path=str(output_path),
            selected_characters=selected_characters,
            name_map=name_map,
            keep_names=args.keep_names,
            custom_title=args.title or None,
            stop_on_name_problems=args.stop_on_name_problems,
        )

    # Display results
    if result["success"]:
        # Worked out before the heading, so the heading cannot say one thing
        # and the list under it another.
        is_transform = args.transform_type not in ("parse_only", "character_analysis")
        problems = run_problems(result) if is_transform else []
        print("\n⚠️  Finished, with problems" if problems else "\n✅ Success!")
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
        else:
            _print_run_report(result, app)
        print(f"  Output: {result['output_path']}")
        _write_decision_sheet(args.transform_type, result.get("output_path"))
        if problems:
            print("\n  Before you use this book:")
            for problem in problems:
                print(f"  - {problem}")
            app.shutdown()
            sys.exit(EXIT_FINISHED_WITH_PROBLEMS)
    else:
        print(f"\n❌ Error: {result['error']}")
        for problem in result.get("name_map_problems") or []:
            print(f"  - {problem}")
        if "llm_provider" in str(result["error"]):
            print(
                "\n  No model is set up. Add ANTHROPIC_API_KEY or OPENAI_API_KEY to a .env file"
                "\n  in this folder (copy .env.example to start), or set DEFAULT_PROVIDER=ollama there."
                "\n  Or run `python regender_cli.py` with no arguments and it will walk you through it."
            )
        sys.exit(1)

    # Clean up
    app.shutdown()


# The book was written, and something about it needs reading first. Distinct
# from 1, which means no book: a script can tell "failed" from "look at this".
EXIT_FINISHED_WITH_PROBLEMS = 2


def _print_run_report(result: dict, app) -> None:
    """What the run did, as the interface reports it: not only that it ended."""
    cast = result.get("cast") or {}
    regendered = f" ({cast['regendered']} regendered)" if cast.get("regendered") else ""
    print(f"  Characters: {result['characters']}{regendered}")
    print(f"  Changes: {result['changes']:,} paragraphs rewritten")

    qc = result.get("quality_control") or {}
    changed, gendered = qc.get("transformed_words"), qc.get("gendered_words")
    if gendered:
        print(f"  Gender words: {changed:,} of {gendered:,} changed ({changed / gendered:.1%})")
    if qc and not qc.get("did_not_run"):
        print(
            f"  QC: {qc.get('structural', 0)} structural, {qc.get('auto_fixable', 0)} "
            f"auto-fixable, {qc.get('needs_review', 0)} to review"
        )
        if qc.get("report"):
            print(f"  QC report: {qc['report']}")
    flagged = result.get("substitutions_to_review")
    if flagged:
        print(f"  To review: {flagged} substitution pair{'' if flagged == 1 else 's'}")

    # The model that was actually called and what it used, read back from the
    # provider rather than from what was asked for.
    try:
        provider = app.get_service("transform").provider
    except Exception:
        provider = None
    if provider is not None:
        if getattr(provider, "model", None):
            print(f"  Model: {provider.model}")
        tokens_in = getattr(provider, "tokens_in", 0) or 0
        tokens_out = getattr(provider, "tokens_out", 0) or 0
        if tokens_in or tokens_out:
            print(
                f"  Usage: {tokens_in:,} tokens in, {tokens_out:,} out, "
                f"{getattr(provider, 'calls', 0) or 0} calls"
            )


def _calc_output_path(input_path: str, transform_type: str) -> Path:
    """Calculate output path from input path and transform type.

    Everything a run produces lands in one folder it owns, with the source it
    started from copied in beside it. See src/utils/paths.py.
    """
    from src.utils.paths import keep_source, run_directory

    input_file = Path(input_path)

    if transform_type == "parse_only":
        # Parsing is not a run: it produces the canonical JSON other runs read.
        if "texts" in str(input_file.parent):
            output_dir = Path(str(input_file.parent).replace("texts", "json"))
        else:
            output_dir = input_file.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / f"{input_file.stem}.json"

    output_dir = run_directory(input_file, transform_type)
    keep_source(input_file, output_dir)
    if transform_type == "character_analysis":
        return output_dir / "characters.json"
    return output_dir / f"{transform_type}.json"


async def async_main():
    """Async main entry point."""
    parser = argparse.ArgumentParser(
        description="Regender-XYZ CLI - Transform gender representation in literature",
        epilog="Exit status: 0 the book was written and nothing needs reading first; "
        "2 the book was written, with problems listed at the end of the output; "
        "1 no book was written.",
    )

    # Main arguments (optional — when omitted, launches interactive TUI)
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
        help="Type of transformation to apply (use parse_only for JSON, character_analysis for character detection)",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (defaults to books/output/<book>-<timestamp>/<transform>.json)",
    )

    # Configuration options
    parser.add_argument("--config", help="Path to configuration file (default: src/config.json)")

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")

    # Selective transformation options
    parser.add_argument(
        "--characters",
        help="Comma-separated list of character names to transform (e.g., 'Dr. Jekyll,Mr. Hyde')",
    )

    parser.add_argument(
        "--characters-file",
        help="Path to file containing character names to transform (one per line)",
    )

    parser.add_argument(
        "--name-map",
        help=(
            "JSON string or path to .json file mapping original character names to replacements, "
            'e.g. \'{"Elizabeth":"Edward","Jane":"John"}\''
        ),
    )

    parser.add_argument(
        "--keep-names",
        action="store_true",
        help="Every character keeps the name the book gives them. Entries passed "
        "with --name-map are still applied; no others are chosen.",
    )

    parser.add_argument(
        "--stop-on-name-problems",
        action="store_true",
        help="Check the finished name map before transforming, and stop if two "
        "characters would share a name or a name would be lost. The map is written "
        "beside the output so it can be corrected and passed back with --name-map.",
    )

    parser.add_argument(
        "--title",
        help="Custom title for the output book (overrides the title extracted from the file)",
    )

    parser.add_argument(
        "--decisions",
        metavar="FILE",
        help=(
            "Apply a filled-in decision sheet to a transformed book. The nonbinary "
            "transform writes <output>_decisions.json listing every word it could "
            "not settle by rule; set a ruling on each entry and pass the file here."
        ),
    )

    parser.add_argument(
        "--estimate",
        action="store_true",
        help="Count the editorial rulings a transform will need, then exit without running it",
    )

    # Parse arguments
    args = parser.parse_args()

    # Validate that transform_type is provided with input
    if args.input is not None and args.transform_type is None:
        parser.error("transform_type is required when input is provided")

    # Set up logging
    setup_logging(args.verbose)

    if args.estimate:
        _report_estimate(args)
        return

    if args.decisions:
        _apply_decisions(args)
        return

    # Process the book (Bill's original path)
    await process_book(args)


def _write_decision_sheet(transform_type: str, output_path: Optional[str]) -> None:
    """List what the transform could not settle by rule, beside the book.

    Written every time, so the work is visible in the output directory rather
    than discovered by reading the finished book.
    """
    from src.services.decision_service import DecisionService

    service = DecisionService(transform_type)
    if transform_type not in service.APPLIES_TO or not output_path:
        return

    book_path = Path(output_path)
    if not book_path.exists():
        return
    try:
        book = json.loads(book_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return

    report = service.scan(book)
    title = book.get("metadata", {}).get("title", "")

    # Written whether or not anything is open, so the export always carries an
    # account of what the transform decided and what it could not.
    note_path = book_path.with_name(book_path.stem + "_TRANSFORM_NOTES.txt")
    note_path.write_text(report.as_note(title), encoding="utf-8")

    if not report.total:
        print(f"\n  No editorial rulings needed.\n  Notes: {note_path}")
        return

    sheet_path = book_path.with_name(book_path.stem + "_decisions.json")
    sheet_path.write_text(
        json.dumps(
            report.to_dict(book.get("metadata", {}).get("title", "")), ensure_ascii=False, indent=1
        ),
        encoding="utf-8",
    )
    print(f"\n  {report.total} words need a ruling from you:")
    for word, number in report.by_word().items():
        print(f"    {number:>5}  {word}")
    print(f"\n  Decision sheet: {sheet_path}")
    print(f"  Notes for readers: {note_path}")
    print("  Set a ruling on each entry, then:")
    print(f"    python regender_cli.py {book_path} {transform_type} --decisions {sheet_path.name}")


def _load_book_text(path: Path) -> str:
    """Raw text of a book file, whether it is .txt or canonical JSON."""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() != ".json":
        return raw
    try:
        book = json.loads(raw)
    except ValueError:
        return raw
    return "\n".join(
        " ".join(p.get("sentences", []))
        for c in book.get("chapters", [])
        for p in c.get("paragraphs", [])
    )


def _report_estimate(args) -> None:
    """Say how much editorial work a transform will ask for, and stop."""
    from src.services.decision_service import DecisionService

    path = Path(args.input)
    if not path.exists():
        print(f"❌ Not found: {path}")
        return

    counts = DecisionService(args.transform_type).estimate(_load_book_text(path))
    total = sum(counts.values())
    if not counts:
        print(f"{args.transform_type} needs no editorial rulings.")
        return

    print(f"\n{args.transform_type} — up to {total} places may need a ruling\n")
    for word, number in counts.items():
        print(f"  {number:>5}  {word}")
    print(
        "\nEnglish has no neutral form of these, so a person decides each one."
        "\nThis is an upper bound: rules and the model settle many in passing."
        "\nThe sheet written after the transform lists what is genuinely left.\n"
    )


def _apply_decisions(args) -> None:
    """Write a filled-in decision sheet into a transformed book."""
    from src.services.decision_service import DecisionService

    book_path, sheet_path = Path(args.input), Path(args.decisions)
    for path in (book_path, sheet_path):
        if not path.exists():
            print(f"❌ Not found: {path}")
            return

    book = json.loads(book_path.read_text(encoding="utf-8"))
    sheet = json.loads(sheet_path.read_text(encoding="utf-8"))

    entries = sheet.get("decisions", [])
    ruled = [e for e in entries if e.get("ruling")]
    if not ruled:
        print(f"No rulings set in {sheet_path.name} — nothing to apply.")
        return

    service = DecisionService(sheet.get("variant", args.transform_type))
    book, applied, problems = service.apply(book, sheet)

    out = book_path.with_name(book_path.stem + "_ruled.json")
    out.write_text(json.dumps(book, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n✅ Applied {applied} of {len(ruled)} rulings")
    if len(entries) - len(ruled):
        print(f"   {len(entries) - len(ruled)} left unruled and unchanged")
    for problem in problems:
        print(f"   ⚠ {problem}")
    print(f"   Output: {out}\n")


def _launch_tui():
    """Launch the interactive TUI (must run outside asyncio event loop)."""
    logging.disable(logging.CRITICAL)

    from src.cli.tui import run_tui

    run_tui()


def main():
    """Main CLI entry point."""
    # Quick check: no args (or just flags) means TUI mode.
    # We must launch TUI before entering asyncio.run() because
    # Textual needs its own event loop.
    if len(sys.argv) == 1:
        _launch_tui()
        return

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
