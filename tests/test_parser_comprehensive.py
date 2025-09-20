#!/usr/bin/env python3
"""Comprehensive test of the integrated parser on diverse books."""

import json
import os
import sys
import traceback
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.parsers.parser import IntegratedParser, ParsedBook


def test_book(file_path: str) -> Dict[str, Any]:
    """
    Test a single book and return results.

    Returns dict with test results and any errors.
    """
    book_name = os.path.basename(file_path)
    result = {
        "book": book_name,
        "success": False,
        "error": None,
        "format": None,
        "confidence": 0,
        "chapters": 0,
        "paragraphs": 0,
        "title": None,
        "author": None,
        "issues": [],
    }

    try:
        # Parse the book
        parser = IntegratedParser()

        with open(file_path, encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()

        if not raw_text:
            result["error"] = "Empty file"
            return result

        result["raw_size"] = len(raw_text)

        # Parse
        parsed = parser.parse(raw_text)

        # Extract results
        result["success"] = True
        result["format"] = parsed.format.value
        result["confidence"] = parsed.format_confidence
        result["chapters"] = len(parsed.chapters)
        result["title"] = parsed.title
        result["author"] = parsed.author
        result["cleaned_size"] = parsed.cleaned_text_length

        # Count paragraphs
        total_paras = sum(len(ch["paragraphs"]) for ch in parsed.chapters)
        result["paragraphs"] = total_paras

        # Check for potential issues
        if result["chapters"] == 0:
            result["issues"].append("No chapters detected")

        if result["paragraphs"] == 0:
            result["issues"].append("No paragraphs detected")

        if result["confidence"] < 50:
            result["issues"].append(f"Low confidence: {result['confidence']}%")

        if result["title"] == "Unknown Title":
            result["issues"].append("Title not extracted")

        if result["author"] == "Unknown Author":
            result["issues"].append("Author not extracted")

        # Check for empty chapters
        empty_chapters = [i for i, ch in enumerate(parsed.chapters) if len(ch["paragraphs"]) == 0]
        if empty_chapters:
            result["issues"].append(f"{len(empty_chapters)} empty chapters")

        # Check average chapter length
        if result["chapters"] > 0:
            avg_paras = result["paragraphs"] / result["chapters"]
            if avg_paras < 10:
                result["issues"].append(f"Very short chapters (avg {avg_paras:.1f} paragraphs)")
            elif avg_paras > 500:
                result["issues"].append(f"Very long chapters (avg {avg_paras:.1f} paragraphs)")

    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()

    return result


def print_summary(results: List[Dict[str, Any]]):
    """Print a summary of test results."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE PARSER TEST SUMMARY")
    print("=" * 80)

    # Overall stats
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total - successful

    print(f"\nTotal books tested: {total}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")

    if failed > 0:
        print("\n⚠️  FAILED BOOKS:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['book']}: {r['error']}")

    # Format detection stats
    print("\n📊 FORMAT DETECTION:")
    formats = {}
    for r in results:
        if r["success"]:
            fmt = r["format"]
            formats[fmt] = formats.get(fmt, 0) + 1

    for fmt, count in sorted(formats.items()):
        print(f"  {fmt}: {count} books")

    # Confidence distribution
    print("\n🎯 CONFIDENCE DISTRIBUTION:")
    conf_ranges = {"90-100%": 0, "70-89%": 0, "50-69%": 0, "<50%": 0}
    for r in results:
        if r["success"]:
            conf = r["confidence"]
            if conf >= 90:
                conf_ranges["90-100%"] += 1
            elif conf >= 70:
                conf_ranges["70-89%"] += 1
            elif conf >= 50:
                conf_ranges["50-69%"] += 1
            else:
                conf_ranges["<50%"] += 1

    for range_name, count in conf_ranges.items():
        print(f"  {range_name}: {count} books")

    # Books with issues
    books_with_issues = [r for r in results if r["success"] and r["issues"]]
    if books_with_issues:
        print(f"\n⚠️  BOOKS WITH ISSUES ({len(books_with_issues)}):")
        for r in books_with_issues[:10]:  # Show first 10
            print(f"\n  {r['book']}:")
            for issue in r["issues"]:
                print(f"    - {issue}")

        if len(books_with_issues) > 10:
            print(f"\n  ... and {len(books_with_issues) - 10} more")

    # Content statistics
    print("\n📚 CONTENT STATISTICS:")
    if successful > 0:
        chapters = [r["chapters"] for r in results if r["success"] and r["chapters"] > 0]
        paragraphs = [r["paragraphs"] for r in results if r["success"] and r["paragraphs"] > 0]

        if chapters:
            print(
                f"  Chapters per book: min={min(chapters)}, max={max(chapters)}, avg={sum(chapters) / len(chapters):.1f}"
            )

        if paragraphs:
            print(
                f"  Paragraphs per book: min={min(paragraphs)}, max={max(paragraphs)}, avg={sum(paragraphs) / len(paragraphs):.0f}"
            )


def main():
    """Run comprehensive parser test."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Test books (from your list)
    test_books = [
        "pg1513-Romeo_and_Juliet.txt",
        "pg1661-The_Adventures_of_Sherlock_Holmes.txt",
        "pg200-The_Project_Gutenberg_Encyclopedia,_Volume_1_of_28.txt",
        "pg55231-A_history_of_the_Peninsular_War,_Vol._3,_Sep._1809-Dec._1810.txt",
        "pg26184-Simple_Sabotage_Field_Manual.txt",
        "pg345-Dracula.txt",
        "pg158-Emma.txt",
        "pg5197-My_Life_—_Volume_1.txt",
        "pg7241-Fables_of_La_Fontaine_—_a_New_Edition,_with_Notes.txt",
        "pg844-The_Importance_of_Being_Earnest_A_Trivial_Comedy_for_Serious_People.txt",
        "pg52026-Matthew_Calbraith_Perry_A_Typical_American_Naval_Officer.txt",
        "pg67979-The_Blue_Castle_a_novel.txt",
        "pg6761-The_Adventures_of_Ferdinand_Count_Fathom_—_Complete.txt",
        "pg2707-The_History_of_Herodotus_—_Volume_1.txt",
        "pg4300-Ulysses.txt",
        "pg16328-Beowulf_An_Anglo-Saxon_Epic_Poem_(768).txt",
        "pg12474-Write_It_Right_A_Little_Blacklist_of_Literary_Faults.txt",
        "pg6593-History_of_Tom_Jones,_a_Foundling.txt",
        "pg2542-A_Doll's_House_a_play.txt",
        "pg1232-The_Prince.txt",
    ]

    results = []

    print("Testing parser on 20 diverse books...")
    print("-" * 40)

    for i, book_name in enumerate(test_books, 1):
        book_path = os.path.join(base_dir, "books/texts", book_name)

        if not os.path.exists(book_path):
            print(f"{i:2}. ❌ {book_name}: File not found")
            results.append({"book": book_name, "success": False, "error": "File not found"})
            continue

        print(f"{i:2}. Testing {book_name}...", end=" ")
        result = test_book(book_path)

        if result["success"]:
            status = "✅"
            info = (
                f"{result['format']} ({result['confidence']:.0f}%), {result['chapters']} chapters"
            )
            if result["issues"]:
                info += f" ⚠️  {len(result['issues'])} issues"
        else:
            status = "❌"
            info = f"ERROR: {result['error'][:50]}"

        print(f"{status} {info}")
        results.append(result)

    # Print summary
    print_summary(results)

    # Save detailed results
    output_path = os.path.join(base_dir, "tests/parser_test_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Detailed results saved to: {output_path}")


if __name__ == "__main__":
    main()
