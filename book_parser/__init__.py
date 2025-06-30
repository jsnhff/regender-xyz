"""
Book Parser Package

A modular, extensible parser for converting various book formats to JSON.
Supports multiple languages, play formats, and edge cases from Project Gutenberg.
"""

from .parser import BookParser

__version__ = "2.0.0"
__all__ = ["BookParser"]