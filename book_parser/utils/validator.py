#!/usr/bin/env python3
"""
Validate JSON book representations against their source texts.

This module compares JSON representations with their source texts to ensure:
1. Chapter count matches
2. Sentence content is preserved
3. No data loss during conversion
"""

import json
import sys
from pathlib import Path
from typing import Dict
from collections import defaultdict

from ..parser import BookParser


class BookValidator:
    """Validates JSON representations against source texts."""
    
    def __init__(self, texts_dir: str = "books/texts", json_dir: str = "books/json"):
        self.texts_dir = Path(texts_dir)
        self.json_dir = Path(json_dir)
        self.parser = BookParser()
    
    def validate_book(self, text_file: Path, json_file: Path) -> Dict:
        """Validate a single book's JSON against its source text.
        
        Returns:
            Dict with validation results
        """
        results = {
            "text_file": str(text_file),
            "json_file": str(json_file),
            "valid": True,
            "errors": [],
            "warnings": [],
            "stats": {}
        }
        
        try:
            # Load JSON data
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Re-parse the source text
            with open(text_file, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            parsed_book = self.parser.parse_text(text_content)
            
            # Compare chapter counts
            json_chapters = len(json_data.get('chapters', []))
            parsed_chapters = len(parsed_book.get('chapters', []))
            
            results['stats']['json_chapters'] = json_chapters
            results['stats']['parsed_chapters'] = parsed_chapters
            
            if json_chapters != parsed_chapters:
                results['errors'].append(
                    f"Chapter count mismatch: JSON has {json_chapters}, "
                    f"re-parsed has {parsed_chapters}"
                )
                results['valid'] = False
            
            # Compare total sentence counts
            json_sentences = sum(len(ch.get('sentences', [])) for ch in json_data.get('chapters', []))
            parsed_sentences = sum(len(ch.get('sentences', [])) for ch in parsed_book.get('chapters', []))
            
            results['stats']['json_sentences'] = json_sentences
            results['stats']['parsed_sentences'] = parsed_sentences
            
            if abs(json_sentences - parsed_sentences) > 5:  # Allow small variance
                results['errors'].append(
                    f"Sentence count mismatch: JSON has {json_sentences}, "
                    f"re-parsed has {parsed_sentences}"
                )
                results['valid'] = False
            elif json_sentences != parsed_sentences:
                results['warnings'].append(
                    f"Minor sentence count difference: JSON has {json_sentences}, "
                    f"re-parsed has {parsed_sentences}"
                )
            
            # Try to import recreate function
            try:
                from ..formatters import recreate_text_from_json
                recreated = recreate_text_from_json(str(json_file), verbose=False)
                
                # Compare content (normalize whitespace)
                original_normalized = ' '.join(text_content.split())
                recreated_normalized = ' '.join(recreated.split())
                
                # Calculate content similarity using a more robust method
                # Compare words instead of characters to handle minor formatting differences
                original_words = original_normalized.split()
                recreated_words = recreated_normalized.split()
                
                # Use set intersection for word-level similarity
                original_set = set(original_words)
                recreated_set = set(recreated_words)
                common_words = original_set & recreated_set
                total_words = original_set | recreated_set
                
                # Calculate Jaccard similarity
                similarity = len(common_words) / len(total_words) if total_words else 0.0
                
                results['stats']['content_similarity'] = round(similarity * 100, 2)
                
                if similarity < 0.85:  # 85% similarity threshold for Jaccard
                    results['errors'].append(
                        f"Content similarity too low: {similarity*100:.1f}%"
                    )
                    results['valid'] = False
                elif similarity < 0.95:
                    results['warnings'].append(
                        f"Minor content differences: {similarity*100:.1f}% similarity"
                    )
            except ImportError:
                results['warnings'].append("Could not import recreate_text_from_json for content validation")
            
            # Check for metadata
            if not json_data.get('metadata', {}).get('title'):
                results['warnings'].append("Missing title in metadata")
            
            # Validate chapter titles
            for i, (json_ch, parsed_ch) in enumerate(zip(json_data.get('chapters', []), 
                                                         parsed_book.get('chapters', []))):
                if json_ch.get('title') != parsed_ch.get('title'):
                    results['warnings'].append(
                        f"Chapter {i+1} title mismatch: "
                        f"'{json_ch.get('title')}' vs '{parsed_ch.get('title')}'"
                    )
            
        except Exception as e:
            results['errors'].append(f"Validation error: {str(e)}")
            results['valid'] = False
        
        return results
    
    def validate_all(self) -> Dict:
        """Validate all books and return summary results."""
        results = {
            "total_books": 0,
            "valid_books": 0,
            "invalid_books": 0,
            "books_with_warnings": 0,
            "individual_results": [],
            "common_errors": defaultdict(int),
            "common_warnings": defaultdict(int)
        }
        
        # Find all JSON files
        json_files = sorted(self.json_dir.glob("*.json"))
        results['total_books'] = len(json_files)
        
        print(f"Validating {len(json_files)} books...")
        print("=" * 70)
        
        for json_file in json_files:
            # Find corresponding text file
            base_name = json_file.stem.replace('_clean', '')
            text_file = self.texts_dir / f"{base_name}.txt"
            
            if not text_file.exists():
                print(f"❌ Missing source text for {json_file.name}")
                results['invalid_books'] += 1
                continue
            
            # Validate
            book_results = self.validate_book(text_file, json_file)
            results['individual_results'].append(book_results)
            
            # Update counters
            if book_results['valid']:
                results['valid_books'] += 1
                status = "✅"
            else:
                results['invalid_books'] += 1
                status = "❌"
            
            if book_results['warnings']:
                results['books_with_warnings'] += 1
            
            # Track common issues
            for error in book_results['errors']:
                error_type = error.split(':')[0]
                results['common_errors'][error_type] += 1
            
            for warning in book_results['warnings']:
                warning_type = warning.split(':')[0]
                results['common_warnings'][warning_type] += 1
            
            # Print progress
            print(f"{status} {json_file.name}: ", end='')
            if book_results['valid']:
                stats = book_results['stats']
                print(f"{stats.get('json_chapters', 0)} chapters, "
                      f"{stats.get('json_sentences', 0)} sentences")
            else:
                print(f"{len(book_results['errors'])} errors")
                for error in book_results['errors'][:2]:  # Show first 2 errors
                    print(f"   - {error}")
        
        return results
    
    def generate_report(self, results: Dict, output_file: str = "validation_report.txt"):
        """Generate a detailed validation report."""
        with open(output_file, 'w') as f:
            f.write("GUTENBERG JSON VALIDATION REPORT\n")
            f.write("=" * 70 + "\n\n")
            
            # Summary
            f.write("SUMMARY\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total books processed: {results['total_books']}\n")
            f.write(f"Valid books: {results['valid_books']} "
                   f"({results['valid_books']/max(1, results['total_books'])*100:.1f}%)\n")
            f.write(f"Invalid books: {results['invalid_books']}\n")
            f.write(f"Books with warnings: {results['books_with_warnings']}\n\n")
            
            # Common issues
            if results['common_errors']:
                f.write("COMMON ERRORS\n")
                f.write("-" * 30 + "\n")
                for error_type, count in sorted(results['common_errors'].items(), 
                                              key=lambda x: x[1], reverse=True):
                    f.write(f"{error_type}: {count} occurrences\n")
                f.write("\n")
            
            if results['common_warnings']:
                f.write("COMMON WARNINGS\n")
                f.write("-" * 30 + "\n")
                for warning_type, count in sorted(results['common_warnings'].items(), 
                                                key=lambda x: x[1], reverse=True):
                    f.write(f"{warning_type}: {count} occurrences\n")
                f.write("\n")
            
            # Detailed results for invalid books
            invalid_books = [r for r in results['individual_results'] if not r['valid']]
            if invalid_books:
                f.write("INVALID BOOKS DETAILS\n")
                f.write("-" * 30 + "\n")
                for book in invalid_books:
                    f.write(f"\n{book['json_file']}\n")
                    for error in book['errors']:
                        f.write(f"  ERROR: {error}\n")
                    for warning in book['warnings']:
                        f.write(f"  WARN: {warning}\n")
            
            f.write("\n" + "=" * 70 + "\n")
            f.write("Report generated successfully.\n")
        
        print(f"\nReport saved to: {output_file}")


def main():
    """Main validation function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate book JSON files against source texts"
    )
    parser.add_argument(
        "--texts-dir", 
        default="book_texts",
        help="Directory containing source text files"
    )
    parser.add_argument(
        "--json-dir",
        default="book_json",
        help="Directory containing JSON files"
    )
    parser.add_argument(
        "--report",
        default="validation_report.txt",
        help="Output report filename"
    )
    parser.add_argument(
        "--single",
        help="Validate a single book (provide base filename without extension)"
    )
    
    args = parser.parse_args()
    
    validator = BookValidator(args.texts_dir, args.json_dir)
    
    if args.single:
        # Validate single book
        text_file = Path(args.texts_dir) / f"{args.single}.txt"
        json_file = Path(args.json_dir) / f"{args.single}_clean.json"
        
        if not text_file.exists() or not json_file.exists():
            print(f"Error: Could not find both files for '{args.single}'")
            return
        
        results = validator.validate_book(text_file, json_file)
        print(json.dumps(results, indent=2))
    else:
        # Validate all books
        results = validator.validate_all()
        validator.generate_report(results, args.report)
        
        print("\n" + "=" * 70)
        print(f"✅ Valid: {results['valid_books']}/{results['total_books']} books")
        print(f"❌ Invalid: {results['invalid_books']} books")
        print(f"⚠️  Warnings: {results['books_with_warnings']} books")


if __name__ == "__main__":
    main()