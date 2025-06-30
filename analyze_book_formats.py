#!/usr/bin/env python3
"""
Analyze book formats across all Gutenberg texts to build a comprehensive parser.

This script:
1. Scans all 100 books to identify patterns
2. Collects statistics on chapter formats, TOCs, special sections
3. Identifies edge cases and variations
4. Outputs a comprehensive analysis for building a refined parser
"""

import re
import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set, Optional
import statistics


class BookFormatAnalyzer:
    """Analyze book formats to understand parsing requirements."""
    
    def __init__(self, texts_dir: str = "gutenberg_texts"):
        self.texts_dir = Path(texts_dir)
        self.books_analyzed = 0
        
        # Pattern collections
        self.chapter_patterns = Counter()
        self.toc_patterns = Counter()
        self.special_sections = Counter()
        self.metadata_patterns = Counter()
        
        # Statistics
        self.chapter_counts = []
        self.avg_chapter_lengths = []
        self.book_structures = []
        
        # Edge cases
        self.edge_cases = defaultdict(list)
        
        # Chapter pattern regexes to test
        self.test_patterns = [
            # Standard patterns
            (r'^CHAPTER\s+(\d+)\.?\s*$', 'CHAPTER_ARABIC'),
            (r'^CHAPTER\s+([IVXLCDM]+)\.?\s*$', 'CHAPTER_ROMAN'),
            (r'^Chapter\s+(\d+)\.?\s*$', 'Chapter_Arabic'),
            (r'^Chapter\s+([IVXLCDM]+)\.?\s*$', 'Chapter_Roman'),
            
            # With titles
            (r'^CHAPTER\s+(\d+)\.\s+(.+)$', 'CHAPTER_ARABIC_TITLED'),
            (r'^CHAPTER\s+([IVXLCDM]+)\.\s+(.+)$', 'CHAPTER_ROMAN_TITLED'),
            (r'^Chapter\s+(\d+)\.\s+(.+)$', 'Chapter_Arabic_Titled'),
            (r'^Chapter\s+([IVXLCDM]+)\.\s+(.+)$', 'Chapter_Roman_Titled'),
            
            # With separators
            (r'^CHAPTER\s+(\d+)\s*[:\-—]\s*(.*)$', 'CHAPTER_ARABIC_SEP'),
            (r'^CHAPTER\s+([IVXLCDM]+)\s*[:\-—]\s*(.*)$', 'CHAPTER_ROMAN_SEP'),
            
            # Just numbers
            (r'^(\d+)\.?\s*$', 'BARE_ARABIC'),
            (r'^([IVXLCDM]+)\.?\s*$', 'BARE_ROMAN'),
            
            # Book/Part patterns
            (r'^BOOK\s+(\d+)\.?\s*$', 'BOOK_ARABIC'),
            (r'^BOOK\s+([IVXLCDM]+)\.?\s*$', 'BOOK_ROMAN'),
            (r'^PART\s+(\d+)\.?\s*$', 'PART_ARABIC'),
            (r'^PART\s+([IVXLCDM]+)\.?\s*$', 'PART_ROMAN'),
            
            # Other variations
            (r'^LETTER\s+(\d+)\.?\s*$', 'LETTER'),
            (r'^EPISODE\s+(\d+)\.?\s*$', 'EPISODE'),
            (r'^SCENE\s+(\d+)\.?\s*$', 'SCENE'),
            (r'^ACT\s+([IVXLCDM]+)\.?\s*$', 'ACT'),
        ]
    
    def analyze_file(self, filepath: Path) -> Dict:
        """Analyze a single book file."""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            return {}
        
        # Remove BOM if present
        if text.startswith('\ufeff'):
            text = text[1:]
        
        lines = text.split('\n')
        
        # Analysis results
        results = {
            'filename': filepath.name,
            'total_lines': len(lines),
            'total_chars': len(text),
            'chapters_found': [],
            'toc_found': False,
            'special_sections': [],
            'metadata': {},
            'structure': []
        }
        
        # Find Gutenberg boundaries
        start_marker = None
        end_marker = None
        
        for i, line in enumerate(lines):
            if '*** START' in line and 'PROJECT GUTENBERG' in line:
                start_marker = i
            elif '*** END' in line and 'PROJECT GUTENBERG' in line:
                end_marker = i
                break
        
        # Focus on main content
        if start_marker:
            content_lines = lines[start_marker:end_marker] if end_marker else lines[start_marker:]
        else:
            content_lines = lines
        
        # Analyze patterns
        self._analyze_metadata(lines[:100], results)
        self._analyze_chapters(content_lines, results)
        self._analyze_toc(content_lines, results)
        self._analyze_special_sections(content_lines, results)
        self._analyze_structure(content_lines, results)
        
        return results
    
    def _analyze_metadata(self, lines: List[str], results: Dict):
        """Analyze metadata patterns."""
        for line in lines:
            # Title
            if re.match(r'^Title:', line, re.IGNORECASE):
                results['metadata']['title'] = line.split(':', 1)[1].strip()
                self.metadata_patterns['Title:'] += 1
            # Author
            elif re.match(r'^Author:', line, re.IGNORECASE):
                results['metadata']['author'] = line.split(':', 1)[1].strip()
                self.metadata_patterns['Author:'] += 1
            # Other patterns
            elif 'eBook' in line and re.search(r'of (.+?)[,\n]', line):
                match = re.search(r'of (.+?)(?:,|\n|$)', line)
                if match and 'title' not in results['metadata']:
                    results['metadata']['title'] = match.group(1).strip()
                    self.metadata_patterns['eBook_of'] += 1
    
    def _analyze_chapters(self, lines: List[str], results: Dict):
        """Analyze chapter patterns."""
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            
            for pattern, pattern_name in self.test_patterns:
                if re.match(pattern, stripped):
                    self.chapter_patterns[pattern_name] += 1
                    
                    # Check if it's a real chapter (has content after)
                    has_content = False
                    if i + 3 < len(lines):
                        next_content = '\n'.join(lines[i+1:i+10])
                        # Real chapter should have prose content
                        if len(next_content) > 100 and not re.match(r'^(CHAPTER|Chapter)', lines[i+2].strip()):
                            has_content = True
                    
                    results['chapters_found'].append({
                        'line': i,
                        'text': stripped,
                        'pattern': pattern_name,
                        'has_content': has_content
                    })
                    break
    
    def _analyze_toc(self, lines: List[str], results: Dict):
        """Analyze table of contents patterns."""
        toc_patterns = [
            r'^CONTENTS\.?$',
            r'^TABLE OF CONTENTS\.?$',
            r'^Contents\.?$',
            r'^INDEX\.?$',
            r'^CHAPTERS?\.?$'
        ]
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            for pattern in toc_patterns:
                if re.match(pattern, stripped, re.IGNORECASE):
                    self.toc_patterns[stripped] += 1
                    results['toc_found'] = True
                    
                    # Analyze TOC structure
                    toc_lines = []
                    for j in range(i+1, min(i+100, len(lines))):
                        if lines[j].strip():
                            # Check if line looks like TOC entry
                            if re.search(r'(CHAPTER|Chapter|\d+|[IVXLCDM]+)', lines[j]):
                                toc_lines.append(lines[j].strip())
                            else:
                                # Check for page numbers
                                if re.search(r'\d{1,3}\s*$', lines[j]):
                                    toc_lines.append(lines[j].strip())
                        
                        # Stop if we hit actual content
                        if len(lines[j]) > 200:
                            break
                    
                    results['toc_structure'] = {
                        'header': stripped,
                        'entries': len(toc_lines),
                        'sample': toc_lines[:5]
                    }
                    break
    
    def _analyze_special_sections(self, lines: List[str], results: Dict):
        """Analyze special sections like PREFACE, INTRODUCTION, etc."""
        special_patterns = [
            'PREFACE', 'INTRODUCTION', 'FOREWORD', 'PROLOGUE', 'EPILOGUE',
            'APPENDIX', 'GLOSSARY', 'BIBLIOGRAPHY', 'NOTES', 'AFTERWORD',
            'DEDICATION', 'ACKNOWLEDGMENTS', 'ETYMOLOGY', 'EXTRACTS'
        ]
        
        for i, line in enumerate(lines):
            stripped = line.strip().upper()
            for pattern in special_patterns:
                if pattern in stripped and len(stripped) < 50:
                    self.special_sections[pattern] += 1
                    results['special_sections'].append({
                        'type': pattern,
                        'line': i,
                        'text': line.strip()
                    })
    
    def _analyze_structure(self, lines: List[str], results: Dict):
        """Analyze overall book structure."""
        # Simple structure detection
        structure = []
        current_section = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Major divisions
            if re.match(r'^(BOOK|PART|VOLUME|SECTION)\s+[IVXLCDM\d]+', stripped, re.IGNORECASE):
                structure.append({
                    'type': 'DIVISION',
                    'text': stripped,
                    'line': i
                })
            # Chapters
            elif any(re.match(p[0], stripped) for p in self.test_patterns[:10]):
                if not current_section or current_section['type'] != 'CHAPTER_BLOCK':
                    current_section = {
                        'type': 'CHAPTER_BLOCK',
                        'start': i,
                        'count': 0
                    }
                    structure.append(current_section)
                current_section['count'] += 1
        
        results['structure'] = structure
    
    def analyze_all_books(self) -> Dict:
        """Analyze all books in the directory."""
        text_files = sorted(self.texts_dir.glob("*.txt"))
        
        print(f"Analyzing {len(text_files)} books...")
        print("-" * 60)
        
        all_results = []
        
        for i, filepath in enumerate(text_files):
            print(f"[{i+1}/{len(text_files)}] Analyzing {filepath.name}...")
            
            results = self.analyze_file(filepath)
            if results:
                all_results.append(results)
                self.books_analyzed += 1
                
                # Collect statistics
                real_chapters = [ch for ch in results['chapters_found'] if ch['has_content']]
                if real_chapters:
                    self.chapter_counts.append(len(real_chapters))
        
        return self._compile_analysis(all_results)
    
    def _compile_analysis(self, all_results: List[Dict]) -> Dict:
        """Compile comprehensive analysis from all books."""
        analysis = {
            'total_books': self.books_analyzed,
            'chapter_patterns': dict(self.chapter_patterns.most_common(20)),
            'toc_patterns': dict(self.toc_patterns.most_common()),
            'special_sections': dict(self.special_sections.most_common()),
            'metadata_patterns': dict(self.metadata_patterns.most_common()),
            'statistics': {
                'books_with_toc': sum(1 for r in all_results if r['toc_found']),
                'books_with_chapters': sum(1 for r in all_results if r['chapters_found']),
                'avg_chapters': statistics.mean(self.chapter_counts) if self.chapter_counts else 0,
                'min_chapters': min(self.chapter_counts) if self.chapter_counts else 0,
                'max_chapters': max(self.chapter_counts) if self.chapter_counts else 0,
            },
            'edge_cases': [],
            'recommendations': []
        }
        
        # Find edge cases
        for result in all_results:
            # Books without chapters
            if not result['chapters_found']:
                analysis['edge_cases'].append({
                    'file': result['filename'],
                    'issue': 'no_chapters_found'
                })
            
            # Books with unusual chapter counts
            real_chapters = [ch for ch in result['chapters_found'] if ch['has_content']]
            if len(real_chapters) > 200:
                analysis['edge_cases'].append({
                    'file': result['filename'],
                    'issue': 'excessive_chapters',
                    'count': len(real_chapters)
                })
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate parser recommendations based on analysis."""
        recommendations = []
        
        # Most common patterns
        top_patterns = list(analysis['chapter_patterns'].keys())[:5]
        recommendations.append(f"Prioritize these chapter patterns: {', '.join(top_patterns)}")
        
        # TOC handling
        toc_percentage = (analysis['statistics']['books_with_toc'] / analysis['total_books']) * 100
        recommendations.append(f"{toc_percentage:.1f}% of books have TOCs - implement robust TOC detection")
        
        # Special sections
        if analysis['special_sections']:
            recommendations.append(f"Handle these special sections: {', '.join(list(analysis['special_sections'].keys())[:5])}")
        
        return recommendations
    
    def save_analysis(self, analysis: Dict, output_file: str = "book_format_analysis.json"):
        """Save analysis to JSON file."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"\nAnalysis saved to {output_file}")
    
    def print_summary(self, analysis: Dict):
        """Print analysis summary."""
        print("\n" + "=" * 60)
        print("BOOK FORMAT ANALYSIS SUMMARY")
        print("=" * 60)
        
        print(f"\nTotal books analyzed: {analysis['total_books']}")
        print(f"Books with TOC: {analysis['statistics']['books_with_toc']}")
        print(f"Books with chapters: {analysis['statistics']['books_with_chapters']}")
        print(f"Average chapters per book: {analysis['statistics']['avg_chapters']:.1f}")
        
        print("\nTop Chapter Patterns:")
        for pattern, count in list(analysis['chapter_patterns'].items())[:5]:
            print(f"  {pattern}: {count} occurrences")
        
        print("\nTop Special Sections:")
        for section, count in list(analysis['special_sections'].items())[:5]:
            print(f"  {section}: {count} occurrences")
        
        print("\nRecommendations:")
        for rec in analysis['recommendations']:
            print(f"  - {rec}")
        
        if analysis['edge_cases']:
            print(f"\nEdge cases found: {len(analysis['edge_cases'])}")
            for case in analysis['edge_cases'][:5]:
                print(f"  - {case['file']}: {case['issue']}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze Gutenberg book formats to build better parser"
    )
    parser.add_argument(
        "-d", "--directory",
        default="gutenberg_texts",
        help="Directory containing text files (default: gutenberg_texts)"
    )
    parser.add_argument(
        "-o", "--output",
        default="book_format_analysis.json",
        help="Output JSON file (default: book_format_analysis.json)"
    )
    parser.add_argument(
        "-s", "--summary",
        action="store_true",
        help="Print summary after analysis"
    )
    
    args = parser.parse_args()
    
    # Run analysis
    analyzer = BookFormatAnalyzer(args.directory)
    analysis = analyzer.analyze_all_books()
    
    # Save results
    analyzer.save_analysis(analysis, args.output)
    
    # Print summary
    if args.summary:
        analyzer.print_summary(analysis)


if __name__ == "__main__":
    main()