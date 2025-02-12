"""Custom exceptions for the text transformer application."""

class TextTransformerError(Exception):
    """Base exception for all text transformer errors."""
    pass

class CharacterAnalysisError(TextTransformerError):
    """Raised when character analysis fails."""
    pass

class TransformationError(TextTransformerError):
    """Raised when text transformation fails."""
    pass
