#!/usr/bin/env python3
"""
Production run: generate all 4 gender-transformed versions of Pride and Prejudice.

Produces RTF files ready for InDesign import:
  books/output/pride-and-prejudice/all_female.rtf
  books/output/pride-and-prejudice/all_male.rtf
  books/output/pride-and-prejudice/nonbinary.rtf
  books/output/pride-and-prejudice/gender_swap.rtf

Run from the project root:
    python scripts/run_pride_prejudice.py

Requires ANTHROPIC_API_KEY or OPENAI_API_KEY in environment / .env file.
QC is enabled by default. Pass --no-qc to skip (faster, ~50% cheaper).
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app import Application  # noqa: E402
from src.exporters import export_book  # noqa: E402

INPUT = Path("books/texts/pg1342-Pride_and_Prejudice.txt")
OUTPUT_DIR = Path("books/output/pride-and-prejudice")
TRANSFORMS = ["all_female", "all_male", "nonbinary", "gender_swap"]


async def run_transform(app: Application, transform_type: str, qc: bool) -> None:
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    output_json = output_dir / f"{transform_type}.json"

    print(f"\n{'='*60}")
    print(f"  {transform_type.upper().replace('_', ' ')}")
    print(f"{'='*60}")

    result = await app.process_book(
        file_path=str(INPUT),
        transform_type=transform_type,
        output_path=str(output_json),
        quality_control=qc,
    )

    if result.get("error"):
        print(f"  ✗ ERROR: {result['error']}")
        return

    changes = result.get("changes", 0)
    qc_score = result.get("quality_score")
    qc_corr = result.get("qc_corrections", 0)

    print(f"  ✓ {changes} changes applied")
    if qc_score is not None:
        print(f"  ✓ QC: {qc_score}% quality ({qc_corr} corrections)")

    # Export RTF
    rtf_path = output_dir / f"{transform_type}.rtf"
    export_book(str(output_json), "rtf", str(rtf_path))
    print(f"  ✓ RTF → {rtf_path}")

    # Also export plain text for proofreading
    txt_path = output_dir / f"{transform_type}.txt"
    export_book(str(output_json), "txt", str(txt_path))
    print(f"  ✓ TXT → {txt_path}")


async def main(transforms: list[str], qc: bool) -> None:
    if not INPUT.exists():
        print(f"ERROR: Input file not found: {INPUT}")
        print("Download it first:  python -m download.download 1342")
        sys.exit(1)

    app = Application("src/config.json")
    print(f"Input:  {INPUT}")
    print(f"Output: {OUTPUT_DIR}/")
    print(f"QC:     {'enabled' if qc else 'disabled'}")
    print(f"Runs:   {', '.join(transforms)}")

    for t in transforms:
        await run_transform(app, t, qc)

    print(f"\n{'='*60}")
    print("  Done. RTF files ready for InDesign.")
    print(f"  {OUTPUT_DIR}/")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate all 4 P&P volumes")
    parser.add_argument("--no-qc", action="store_true", help="Skip quality control pass")
    parser.add_argument(
        "--only",
        choices=TRANSFORMS,
        metavar="TYPE",
        help=f"Run only one transform: {', '.join(TRANSFORMS)}",
    )
    args = parser.parse_args()

    transforms = [args.only] if args.only else TRANSFORMS
    qc = not args.no_qc

    logging.basicConfig(level=logging.WARNING)  # suppress noise; errors still show
    asyncio.run(main(transforms, qc))
