"""
Gutenberg utilities for downloading books from Project Gutenberg.

This package provides functionality for downloading books from Project Gutenberg's
website, handling URL patterns, and managing downloads.
"""

from .download import GutenbergDownloader

__version__ = "2.0.0"
__all__ = ["GutenbergDownloader"]