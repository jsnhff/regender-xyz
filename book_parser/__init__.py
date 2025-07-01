"""
Book Parser Package

A modular, extensible parser for converting various book formats to JSON.
Includes validation and batch processing capabilities.
"""

from .parser import BookParser
from .utils.validator import BookValidator
from .utils.batch_processor import process_all_books, generate_summary_report
from .formatters import recreate_text_from_json, save_book_json, load_book_json

__version__ = "2.0.0"
__all__ = [
    "BookParser",
    "BookValidator", 
    "process_all_books",
    "generate_summary_report",
    "recreate_text_from_json",
    "save_book_json",
    "load_book_json"
]