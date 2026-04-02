"""
Centralized error handling for the regender-xyz application.

This module provides custom exception types and error handling utilities
for consistent error management across all services.
"""

import logging
import traceback
import uuid
from typing import Any, Dict, Optional


class RegenderError(Exception):
    """Base exception for all regender-xyz errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "GENERAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        """
        Initialize RegenderError.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
            correlation_id: Request correlation ID for tracing
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.correlation_id = correlation_id or str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "correlation_id": self.correlation_id,
        }


class ValidationError(RegenderError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        """Initialize ValidationError with field information."""
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        super().__init__(
            message=message, error_code="VALIDATION_ERROR", details=details, **kwargs
        )


class ProviderError(RegenderError):
    """Raised when LLM provider operations fail."""

    def __init__(self, message: str, provider: Optional[str] = None, **kwargs):
        """Initialize ProviderError with provider information."""
        details = kwargs.pop("details", {})
        if provider:
            details["provider"] = provider
        super().__init__(
            message=message, error_code="PROVIDER_ERROR", details=details, **kwargs
        )


class CharacterExtractionError(RegenderError):
    """Raised when character extraction fails."""

    def __init__(self, message: str, chunk_idx: Optional[int] = None, **kwargs):
        """Initialize CharacterExtractionError with chunk information."""
        details = kwargs.pop("details", {})
        if chunk_idx is not None:
            details["chunk_index"] = chunk_idx
        super().__init__(
            message=message,
            error_code="CHARACTER_EXTRACTION_ERROR",
            details=details,
            **kwargs,
        )


class TransformationError(RegenderError):
    """Raised when text transformation fails."""

    def __init__(self, message: str, transform_type: Optional[str] = None, **kwargs):
        """Initialize TransformationError with transformation type."""
        details = kwargs.pop("details", {})
        if transform_type:
            details["transform_type"] = transform_type
        super().__init__(
            message=message,
            error_code="TRANSFORMATION_ERROR",
            details=details,
            **kwargs,
        )


class ConfigurationError(RegenderError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        """Initialize ConfigurationError with configuration key."""
        details = kwargs.pop("details", {})
        if config_key:
            details["config_key"] = config_key
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=details,
            **kwargs,
        )


class RateLimitError(ProviderError):
    """Raised when provider rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        """Initialize RateLimitError with retry information."""
        details = kwargs.pop("details", {})
        if retry_after:
            details["retry_after_seconds"] = retry_after
        kwargs["error_code"] = "RATE_LIMIT_ERROR"
        super().__init__(message=message, **kwargs)


class TimeoutError(RegenderError):
    """Raised when an operation times out."""

    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        """Initialize TimeoutError with operation information."""
        details = kwargs.pop("details", {})
        if operation:
            details["operation"] = operation
        super().__init__(
            message=message, error_code="TIMEOUT_ERROR", details=details, **kwargs
        )


class ErrorHandler:
    """Centralized error handling utilities."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize ErrorHandler with optional logger."""
        self.logger = logger or logging.getLogger(__name__)

    def handle_error(
        self, error: Exception, correlation_id: Optional[str] = None
    ) -> RegenderError:
        """
        Convert any exception to a RegenderError.

        Args:
            error: The exception to handle
            correlation_id: Request correlation ID

        Returns:
            RegenderError instance
        """
        if isinstance(error, RegenderError):
            return error

        # Handle specific Python exceptions
        if isinstance(error, ValueError):
            return ValidationError(
                message=str(error),
                details={"original_type": type(error).__name__},
                correlation_id=correlation_id,
            )

        if isinstance(error, TimeoutError):
            return TimeoutError(
                message=str(error),
                details={"original_type": type(error).__name__},
                correlation_id=correlation_id,
            )

        # Generic exception
        return RegenderError(
            message=str(error),
            error_code="INTERNAL_ERROR",
            details={
                "original_type": type(error).__name__,
                "traceback": traceback.format_exc(),
            },
            correlation_id=correlation_id,
        )

    def log_error(self, error: RegenderError, level: str = "ERROR"):
        """
        Log error with structured information.

        Args:
            error: The error to log
            level: Logging level (ERROR, WARNING, INFO)
        """
        log_method = getattr(self.logger, level.lower(), self.logger.error)
        log_method(
            f"[{error.error_code}] {error.message}",
            extra={
                "correlation_id": error.correlation_id,
                "details": error.details,
                "error_code": error.error_code,
            },
        )

    def create_error_response(
        self, error: RegenderError, include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Create standardized error response.

        Args:
            error: The error to format
            include_details: Whether to include detailed error information

        Returns:
            Dictionary suitable for API response
        """
        response = {
            "success": False,
            "error": error.error_code,
            "message": error.message,
            "correlation_id": error.correlation_id,
        }

        if include_details:
            response["details"] = error.details

        return response


# Circuit breaker implementation for provider reliability
class CircuitBreaker:
    """Circuit breaker pattern for handling provider failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = ProviderError,
    ):
        """
        Initialize CircuitBreaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to monitor
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            ProviderError: If circuit is open
        """
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise ProviderError(
                    "Circuit breaker is open",
                    details={
                        "failure_count": self.failure_count,
                        "last_failure": self.last_failure_time,
                    },
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        import time

        return (
            self.last_failure_time
            and time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        """Reset circuit breaker on successful call."""
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        """Record failure and potentially open circuit."""
        import time

        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"


# Retry decorator with exponential backoff
def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (ProviderError, RateLimitError),
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to retry on
    """
    import asyncio
    import functools
    import time

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(min(delay, max_delay))
                        delay *= exponential_base

            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(min(delay, max_delay))
                        delay *= exponential_base

            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator