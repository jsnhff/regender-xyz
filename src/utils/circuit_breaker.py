"""
Circuit Breaker Pattern Implementation

Protects against cascading API failures by monitoring failure rates and
temporarily stopping requests when failure thresholds are exceeded.

The circuit breaker has three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Failing fast, requests are rejected immediately
- HALF_OPEN: Testing recovery, limited requests allowed

This implementation is thread-safe and supports async operations.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

# Configure logger
logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    # Failure thresholds
    failure_threshold: int = 5  # Consecutive failures to open circuit
    success_threshold: int = 3  # Consecutive successes to close from half-open

    # Time windows
    timeout_duration: float = 60.0  # Seconds to wait before trying half-open
    reset_timeout: float = 300.0  # Seconds to reset failure count if successful

    # Monitoring windows
    monitoring_window: float = 60.0  # Time window for tracking failures
    half_open_max_calls: int = 3  # Max calls allowed in half-open state

    # Error handling
    expected_exceptions: tuple = (Exception,)  # Which exceptions count as failures
    ignore_exceptions: tuple = ()  # Exceptions that don't count as failures


@dataclass
class CircuitBreakerMetrics:
    """Metrics and state tracking for circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_change_time: float = field(default_factory=time.time)
    half_open_calls: int = 0

    # Statistics
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    circuit_open_count: int = 0


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and rejecting calls."""

    def __init__(self, message: str = "Circuit breaker is open"):
        super().__init__(message)
        self.message = message


class CircuitBreaker:
    """
    Thread-safe circuit breaker implementation with async support.

    Monitors function calls and opens the circuit when failure thresholds
    are exceeded, providing fail-fast behavior to prevent cascading failures.
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None, name: str = "default"):
        """
        Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
            name: Name for logging and identification
        """
        self.config = config or CircuitBreakerConfig()
        self.name = name
        self.metrics = CircuitBreakerMetrics()
        self._lock = threading.RLock()
        self._async_lock = asyncio.Lock()

        logger.info(f"Circuit breaker '{name}' initialized with config: {self.config}")

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset from open state."""
        if self.metrics.last_failure_time is None:
            return True

        time_since_failure = time.time() - self.metrics.last_failure_time
        return time_since_failure >= self.config.timeout_duration

    def _record_success(self) -> None:
        """Record a successful call and update state if needed."""
        current_time = time.time()

        with self._lock:
            self.metrics.total_calls += 1
            self.metrics.total_successes += 1
            self.metrics.last_success_time = current_time

            if self.metrics.state == CircuitState.CLOSED:
                # Reset failure count on success in closed state
                self.metrics.failure_count = 0

            elif self.metrics.state == CircuitState.HALF_OPEN:
                self.metrics.success_count += 1

                # Close circuit if enough successes in half-open
                if self.metrics.success_count >= self.config.success_threshold:
                    self._close_circuit()

            logger.debug(
                f"Circuit breaker '{self.name}': Success recorded. State: {self.metrics.state}"
            )

    def _record_failure(self, exception: Exception) -> None:
        """Record a failed call and update state if needed."""
        # Check if this exception should be ignored
        if isinstance(exception, self.config.ignore_exceptions):
            logger.debug(
                f"Circuit breaker '{self.name}': Ignoring exception {type(exception).__name__}"
            )
            return

        # Check if this is an expected failure type
        if not isinstance(exception, self.config.expected_exceptions):
            logger.debug(
                f"Circuit breaker '{self.name}': Unexpected exception type "
                f"{type(exception).__name__}"
            )
            return

        current_time = time.time()

        with self._lock:
            self.metrics.total_calls += 1
            self.metrics.total_failures += 1
            self.metrics.last_failure_time = current_time

            if self.metrics.state == CircuitState.CLOSED:
                self.metrics.failure_count += 1

                # Open circuit if failure threshold exceeded
                if self.metrics.failure_count >= self.config.failure_threshold:
                    self._open_circuit()

            elif self.metrics.state == CircuitState.HALF_OPEN:
                # Go back to open on any failure in half-open
                self._open_circuit()

            logger.debug(
                f"Circuit breaker '{self.name}': Failure recorded. "
                f"State: {self.metrics.state}, Failures: {self.metrics.failure_count}"
            )

    def _open_circuit(self) -> None:
        """Open the circuit breaker."""
        with self._lock:
            if self.metrics.state != CircuitState.OPEN:
                previous_state = self.metrics.state
                self.metrics.state = CircuitState.OPEN
                self.metrics.state_change_time = time.time()
                self.metrics.circuit_open_count += 1
                self.metrics.half_open_calls = 0

                logger.warning(
                    f"Circuit breaker '{self.name}': Opening circuit. "
                    f"Previous state: {previous_state}, Failures: {self.metrics.failure_count}"
                )

    def _close_circuit(self) -> None:
        """Close the circuit breaker."""
        with self._lock:
            if self.metrics.state != CircuitState.CLOSED:
                previous_state = self.metrics.state
                self.metrics.state = CircuitState.CLOSED
                self.metrics.state_change_time = time.time()
                self.metrics.failure_count = 0
                self.metrics.success_count = 0
                self.metrics.half_open_calls = 0

                logger.info(
                    f"Circuit breaker '{self.name}': Closing circuit. "
                    f"Previous state: {previous_state}"
                )

    def _half_open_circuit(self) -> None:
        """Set circuit breaker to half-open state."""
        with self._lock:
            if self.metrics.state != CircuitState.HALF_OPEN:
                previous_state = self.metrics.state
                self.metrics.state = CircuitState.HALF_OPEN
                self.metrics.state_change_time = time.time()
                self.metrics.success_count = 0
                self.metrics.half_open_calls = 0

                logger.info(
                    f"Circuit breaker '{self.name}': Half-opening circuit. "
                    f"Previous state: {previous_state}"
                )

    def _can_execute(self) -> bool:
        """Check if a call can be executed based on current state."""
        with self._lock:
            if self.metrics.state == CircuitState.CLOSED:
                return True

            elif self.metrics.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._half_open_circuit()
                    return True
                else:
                    return False

            elif self.metrics.state == CircuitState.HALF_OPEN:
                if self.metrics.half_open_calls < self.config.half_open_max_calls:
                    self.metrics.half_open_calls += 1
                    return True
                else:
                    return False

            return False

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: When circuit is open
            Exception: Original function exceptions
        """
        if not self._can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is open. "
                f"Failures: {self.metrics.total_failures}, "
                f"Last failure: {self.metrics.last_failure_time}"
            )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result

        except Exception as e:
            self._record_failure(e)
            raise

    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute an async function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: When circuit is open
            Exception: Original function exceptions
        """
        if not self._can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is open. "
                f"Failures: {self.metrics.total_failures}, "
                f"Last failure: {self.metrics.last_failure_time}"
            )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            self._record_success()
            return result

        except Exception as e:
            self._record_failure(e)
            raise

    def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self.metrics.state

    def get_metrics(self) -> dict[str, Any]:
        """Get circuit breaker metrics for monitoring."""
        with self._lock:
            total_calls = self.metrics.total_calls
            failure_rate = (self.metrics.total_failures / total_calls) if total_calls > 0 else 0.0
            uptime = time.time() - self.metrics.state_change_time

            return {
                "name": self.name,
                "state": self.metrics.state.value,
                "failure_count": self.metrics.failure_count,
                "success_count": self.metrics.success_count,
                "total_calls": total_calls,
                "total_failures": self.metrics.total_failures,
                "total_successes": self.metrics.total_successes,
                "failure_rate": failure_rate,
                "circuit_open_count": self.metrics.circuit_open_count,
                "last_failure_time": self.metrics.last_failure_time,
                "last_success_time": self.metrics.last_success_time,
                "state_uptime": uptime,
                "half_open_calls": self.metrics.half_open_calls,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "success_threshold": self.config.success_threshold,
                    "timeout_duration": self.config.timeout_duration,
                },
            }

    def reset(self) -> None:
        """Reset circuit breaker to closed state and clear metrics."""
        with self._lock:
            logger.info(f"Circuit breaker '{self.name}': Manual reset")
            self.metrics = CircuitBreakerMetrics()

    def force_open(self) -> None:
        """Force circuit breaker to open state."""
        logger.warning(f"Circuit breaker '{self.name}': Forced open")
        self._open_circuit()

    def force_close(self) -> None:
        """Force circuit breaker to closed state."""
        logger.info(f"Circuit breaker '{self.name}': Forced close")
        self._close_circuit()


def circuit_breaker(config: Optional[CircuitBreakerConfig] = None, name: str = "default"):
    """
    Decorator to apply circuit breaker pattern to functions.

    Args:
        config: Circuit breaker configuration
        name: Name for the circuit breaker instance

    Returns:
        Decorated function with circuit breaker protection
    """
    cb = CircuitBreaker(config, name)

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await cb.call_async(func, *args, **kwargs)

            # Attach circuit breaker to wrapper for access
            async_wrapper._circuit_breaker = cb
            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return cb.call(func, *args, **kwargs)

            # Attach circuit breaker to wrapper for access
            sync_wrapper._circuit_breaker = cb
            return sync_wrapper

    return decorator


# Global registry for named circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """
    Get or create a named circuit breaker instance.

    Args:
        name: Circuit breaker name
        config: Configuration (only used for new instances)

    Returns:
        CircuitBreaker instance
    """
    with _registry_lock:
        if name not in _circuit_breakers:
            _circuit_breakers[name] = CircuitBreaker(config, name)
        return _circuit_breakers[name]


def get_all_circuit_breakers() -> dict[str, CircuitBreaker]:
    """Get all registered circuit breakers."""
    with _registry_lock:
        return _circuit_breakers.copy()


def reset_all_circuit_breakers() -> None:
    """Reset all registered circuit breakers."""
    with _registry_lock:
        for cb in _circuit_breakers.values():
            cb.reset()
        logger.info("All circuit breakers reset")
