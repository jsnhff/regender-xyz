"""
Book downloader utilities for downloading books from online sources.

This package provides functionality for downloading books from Project Gutenberg
and potentially other sources, handling URL patterns, and managing downloads.
"""

from .download import GutenbergDownloader

__version__ = "2.0.0"
__all__ = ["GutenbergDownloader"]