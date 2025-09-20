#!/usr/bin/env python3
"""Test parser on ALL books in books/texts directory."""

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parsers.parser import IntegratedParser


def test_book(file_path: str) -> Dict[str, Any]:
    """Test a single book and return results."""
    book_name = os.path.basename(file_path)
    result = {
        "book": book_name,
        "success": False,
        "error": None,
        "traceback": None,
        "format": None,
        "confidence": 0,
        "chapters": 0,
        "paragraphs": 0,
        "title": None,
        "author": None,
        "empty_chapters": 0,
        "file_size": os.path.getsize(file_path),
    }

    try:
        parser = IntegratedParser()

        with open(file_path, encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()

        if not raw_text:
            result["error"] = "Empty file"
            return result

        # Parse the book
        parsed = parser.parse(raw_text)

        # Extract results
        result["success"] = True
        result["format"] = parsed.format.value
        result["confidence"] = parsed.format_confidence
        result["chapters"] = len(parsed.chapters)
        result["title"] = parsed.title
        result["author"] = parsed.author

        # Count paragraphs and empty chapters
        total_paras = 0
        empty_chapters = 0
        for ch in parsed.chapters:
            para_count = len(ch["paragraphs"])
            total_paras += para_count
            if para_count == 0:
                empty_chapters += 1

        result["paragraphs"] = total_paras
        result["empty_chapters"] = empty_chapters

    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()

    return result


def main():
    """Run parser on all books."""
    books_dir = Path("books/texts")

    # Get all .txt files
    book_files = sorted(books_dir.glob("*.txt"))
    total_books = len(book_files)

    print(f"Testing {total_books} books...")
    print("=" * 80)

    results = []
    errors = []

    for i, book_file in enumerate(book_files, 1):
        print(f"[{i}/{total_books}] Testing {book_file.name}...", end=" ")

        result = test_book(str(book_file))
        results.append(result)

        if result["success"]:
            print(
                f"✓ {result['format']} ({result['confidence']:.0f}%) - {result['chapters']} chapters"
            )
        else:
            print(f"✗ ERROR: {result['error']}")
            errors.append(result)

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print("\n📊 OVERALL:")
    print(f"  Total books: {total_books}")
    print(f"  ✅ Successful: {len(successful)}")
    print(f"  ❌ Failed: {len(failed)}")
    print(f"  Success rate: {len(successful) / total_books * 100:.1f}%")

    # Format distribution
    if successful:
        formats = {}
        for r in successful:
            fmt = r["format"]
            formats[fmt] = formats.get(fmt, 0) + 1

        print("\n📚 FORMAT DISTRIBUTION:")
        for fmt, count in sorted(formats.items(), key=lambda x: -x[1]):
            print(f"  {fmt}: {count} books ({count / len(successful) * 100:.1f}%)")

    # Confidence analysis
    if successful:
        confidences = [r["confidence"] for r in successful]
        print("\n🎯 CONFIDENCE SCORES:")
        print(f"  Average: {sum(confidences) / len(confidences):.1f}%")
        print(f"  Min: {min(confidences):.1f}%")
        print(f"  Max: {max(confidences):.1f}%")
        low_conf = [r for r in successful if r["confidence"] < 50]
        print(f"  Low confidence (<50%): {len(low_conf)} books")

    # Content statistics
    if successful:
        chapters = [r["chapters"] for r in successful if r["chapters"] > 0]
        paragraphs = [r["paragraphs"] for r in successful if r["paragraphs"] > 0]

        print("\n📖 CONTENT STATISTICS:")
        if chapters:
            print(
                f"  Chapters per book: avg={sum(chapters) / len(chapters):.1f}, min={min(chapters)}, max={max(chapters)}"
            )
        if paragraphs:
            print(
                f"  Paragraphs per book: avg={sum(paragraphs) / len(paragraphs):.0f}, min={min(paragraphs)}, max={max(paragraphs)}"
            )

    # Metadata extraction
    if successful:
        no_title = [r for r in successful if r["title"] == "Unknown Title"]
        no_author = [r for r in successful if r["author"] == "Unknown Author"]

        print("\n🏷️ METADATA EXTRACTION:")
        print(f"  Books with title: {len(successful) - len(no_title)}/{len(successful)}")
        print(f"  Books with author: {len(successful) - len(no_author)}/{len(successful)}")

    # Quality issues
    issues = []
    for r in successful:
        if r["empty_chapters"] > 0:
            issues.append(f"  {r['book']}: {r['empty_chapters']} empty chapters")
        if r["chapters"] == 0:
            issues.append(f"  {r['book']}: No chapters detected")
        if r["paragraphs"] == 0:
            issues.append(f"  {r['book']}: No paragraphs detected")

    if issues:
        print(f"\n⚠️ QUALITY ISSUES ({len(issues)} books):")
        for issue in issues[:10]:  # Show first 10
            print(issue)
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")

    # Show errors
    if failed:
        print(f"\n❌ ERRORS ({len(failed)} books):")
        for r in failed:
            print(f"  {r['book']}: {r['error']}")
            if "--verbose" in sys.argv:
                print(f"    Traceback: {r['traceback'][:200]}...")

    # Save results
    output_file = "tests/all_books_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Detailed results saved to: {output_file}")

    return len(failed)


if __name__ == "__main__":
    sys.exit(main())
