"""
Custom exceptions for the regender-xyz application.
Provides structured error handling across all services.
"""

from typing import Any, Dict, Optional


class RegenderError(Exception):
    """Base exception for all regender-xyz errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}


class ValidationError(RegenderError):
    """Raised when input validation fails."""

    pass


class APIKeyError(ValidationError):
    """Raised when API key validation fails."""

    pass


class ProviderError(RegenderError):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, provider: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, context)
        self.provider = provider


class RateLimitError(ProviderError):
    """Raised when provider rate limits are exceeded."""

    pass


class AuthenticationError(ProviderError):
    """Raised when provider authentication fails."""

    pass


class ServiceError(RegenderError):
    """Base exception for service-level errors."""

    pass


class ParsingError(ServiceError):
    """Raised when text parsing fails."""

    pass


class CharacterAnalysisError(ServiceError):
    """Raised when character analysis fails."""

    pass


class TransformationError(ServiceError):
    """Raised when text transformation fails."""

    pass


class QualityControlError(ServiceError):
    """Raised when quality control validation fails."""

    pass


class ConfigurationError(RegenderError):
    """Raised when configuration is invalid."""

    pass
