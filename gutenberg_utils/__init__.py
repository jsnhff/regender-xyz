"""
Gutenberg Utilities Package

Tools for downloading, processing, and analyzing Project Gutenberg books.
"""

from .download_gutenberg_books import GutenbergDownloader
from .collect_gutenberg_texts import collect_gutenberg_texts as collect_texts
from .process_all_gutenberg import process_all_books
from .analyze_book_formats import BookFormatAnalyzer

__version__ = "1.0.0"
__all__ = [
    "GutenbergDownloader",
    "collect_texts",
    "process_all_books",
    "BookFormatAnalyzer"
]