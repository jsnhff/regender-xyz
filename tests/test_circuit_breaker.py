#!/usr/bin/env python3
"""
Test script for circuit breaker implementation.

This script tests the circuit breaker functionality with mock failures
and validates proper state transitions.
"""

import asyncio
import time
import unittest
from unittest.mock import Mock, patch
from typing import Any

# Add the src directory to the path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)
from src.utils.circuit_breaker_monitor import (
    CircuitBreakerMonitor,
    get_circuit_breaker_monitor,
)
from src.providers.llm_client import (
    UnifiedLLMClient,
    APIError,
    RateLimitError,
    NetworkTimeoutError,
    ServiceUnavailableError,
)


class TestCircuitBreaker(unittest.TestCase):
    """Test the circuit breaker implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_duration=0.1,  # Short timeout for testing
            half_open_max_calls=2,
        )
        self.cb = CircuitBreaker(self.config, "test_circuit")

    def test_initial_state(self):
        """Test circuit breaker starts in closed state."""
        self.assertEqual(self.cb.get_state(), CircuitState.CLOSED)

    def test_successful_calls(self):
        """Test successful calls don't change state."""
        mock_func = Mock(return_value="success")

        for _ in range(5):
            result = self.cb.call(mock_func, "arg1", kwarg1="value1")
            self.assertEqual(result, "success")
            self.assertEqual(self.cb.get_state(), CircuitState.CLOSED)

        self.assertEqual(mock_func.call_count, 5)

    def test_failure_threshold_opens_circuit(self):
        """Test circuit opens after failure threshold."""
        mock_func = Mock(side_effect=Exception("Test failure"))

        # Should open after 3 failures (threshold)
        for i in range(3):
            with self.assertRaises(Exception):
                self.cb.call(mock_func)
            if i < 2:
                self.assertEqual(self.cb.get_state(), CircuitState.CLOSED)

        # Circuit should now be open
        self.assertEqual(self.cb.get_state(), CircuitState.OPEN)

    def test_open_circuit_rejects_calls(self):
        """Test open circuit rejects calls immediately."""
        # Force circuit open
        self.cb.force_open()
        self.assertEqual(self.cb.get_state(), CircuitState.OPEN)

        mock_func = Mock(return_value="success")

        with self.assertRaises(CircuitBreakerOpenError):
            self.cb.call(mock_func)

        # Function should not have been called
        mock_func.assert_not_called()

    def test_half_open_transition(self):
        """Test transition to half-open after timeout."""
        # Force circuit open
        self.cb.force_open()
        self.assertEqual(self.cb.get_state(), CircuitState.OPEN)

        # Wait for timeout
        time.sleep(0.15)

        mock_func = Mock(return_value="success")

        # First call should transition to half-open
        result = self.cb.call(mock_func)
        self.assertEqual(result, "success")
        self.assertEqual(self.cb.get_state(), CircuitState.HALF_OPEN)

    def test_half_open_to_closed_on_success(self):
        """Test half-open transitions to closed on enough successes."""
        # Get to half-open state
        self.cb._half_open_circuit()
        self.assertEqual(self.cb.get_state(), CircuitState.HALF_OPEN)

        mock_func = Mock(return_value="success")

        # Need 2 successes to close (per config)
        for i in range(2):
            result = self.cb.call(mock_func)
            self.assertEqual(result, "success")

        # Should be closed now
        self.assertEqual(self.cb.get_state(), CircuitState.CLOSED)

    def test_half_open_to_open_on_failure(self):
        """Test half-open transitions back to open on failure."""
        # Get to half-open state
        self.cb._half_open_circuit()
        self.assertEqual(self.cb.get_state(), CircuitState.HALF_OPEN)

        mock_func = Mock(side_effect=Exception("Test failure"))

        # Single failure should go back to open
        with self.assertRaises(Exception):
            self.cb.call(mock_func)

        self.assertEqual(self.cb.get_state(), CircuitState.OPEN)

    def test_metrics_collection(self):
        """Test metrics are properly collected."""
        mock_func_success = Mock(return_value="success")
        mock_func_failure = Mock(side_effect=Exception("Test failure"))

        # Make some calls
        self.cb.call(mock_func_success)
        self.cb.call(mock_func_success)

        try:
            self.cb.call(mock_func_failure)
        except Exception:
            pass

        metrics = self.cb.get_metrics()

        self.assertEqual(metrics["total_calls"], 3)
        self.assertEqual(metrics["total_successes"], 2)
        self.assertEqual(metrics["total_failures"], 1)
        self.assertAlmostEqual(metrics["failure_rate"], 1/3, places=2)

    def test_reset_circuit_breaker(self):
        """Test circuit breaker reset functionality."""
        # Force open and add some metrics
        self.cb.force_open()
        self.cb.metrics.total_calls = 10
        self.cb.metrics.total_failures = 5

        # Reset
        self.cb.reset()

        self.assertEqual(self.cb.get_state(), CircuitState.CLOSED)
        metrics = self.cb.get_metrics()
        self.assertEqual(metrics["total_calls"], 0)
        self.assertEqual(metrics["total_failures"], 0)


class TestCircuitBreakerWithLLMClient(unittest.TestCase):
    """Test circuit breaker integration with LLM client."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset any existing circuit breakers
        reset_all_circuit_breakers()

    @patch('src.providers.llm_client._OpenAIClient')
    @patch('src.providers.llm_client._AnthropicClient')
    def test_llm_client_circuit_breaker_integration(self, mock_anthropic, mock_openai):
        """Test LLM client with circuit breaker."""
        # Mock the client to be available
        mock_openai_instance = Mock()
        mock_openai_instance.is_available.return_value = True
        mock_openai_instance.get_default_model.return_value = "gpt-4"
        mock_openai.return_value = mock_openai_instance

        # Set up environment for OpenAI
        with patch.dict('os.environ', {'DEFAULT_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key'}):
            client = UnifiedLLMClient(enable_circuit_breaker=True)
            self.assertIsNotNone(client._circuit_breaker)

    @patch('src.providers.llm_client._OpenAIClient')
    def test_circuit_breaker_fallback_response(self, mock_openai):
        """Test fallback response when circuit breaker is open."""
        # Mock the client
        mock_openai_instance = Mock()
        mock_openai_instance.is_available.return_value = True
        mock_openai_instance.get_default_model.return_value = "gpt-4"
        mock_openai_instance.complete.side_effect = ServiceUnavailableError("Service down")
        mock_openai.return_value = mock_openai_instance

        with patch.dict('os.environ', {'DEFAULT_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key'}):
            client = UnifiedLLMClient(enable_circuit_breaker=True)

            # Trigger failures to open circuit
            messages = [{"role": "user", "content": "test"}]

            for _ in range(5):  # Exceed failure threshold
                try:
                    client.complete(messages)
                except (APIError, ServiceUnavailableError):
                    pass

            # Circuit should be open, next call should return fallback
            response = client.complete(messages, use_fallback=True)
            self.assertEqual(response.model, "fallback")
            self.assertIn("experiencing issues", response.content)

    def test_rate_limit_errors_ignored(self):
        """Test that rate limit errors don't count as failures."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            ignore_exceptions=(RateLimitError,),
        )
        cb = CircuitBreaker(config, "rate_limit_test")

        mock_func = Mock(side_effect=RateLimitError("Rate limited"))

        # Rate limit errors shouldn't open circuit
        for _ in range(5):
            with self.assertRaises(RateLimitError):
                cb.call(mock_func)

        # Circuit should still be closed
        self.assertEqual(cb.get_state(), CircuitState.CLOSED)


class TestCircuitBreakerMonitor(unittest.TestCase):
    """Test circuit breaker monitoring functionality."""

    def setUp(self):
        """Set up test fixtures."""
        reset_all_circuit_breakers()
        self.monitor = CircuitBreakerMonitor()

    def test_health_summary(self):
        """Test health summary generation."""
        # Create a few circuit breakers in different states
        cb1 = get_circuit_breaker("test_healthy")
        cb2 = get_circuit_breaker("test_failed")
        cb3 = get_circuit_breaker("test_degraded")

        # Force different states
        cb2.force_open()  # Failed
        cb3._half_open_circuit()  # Degraded

        summary = self.monitor.get_health_summary()

        self.assertEqual(summary["total_circuit_breakers"], 3)
        self.assertEqual(summary["healthy"], 1)
        self.assertEqual(summary["degraded"], 1)
        self.assertEqual(summary["failed"], 1)

    def test_reset_all_circuit_breakers_monitor(self):
        """Test resetting all circuit breakers through monitor."""
        # Create and modify some circuit breakers
        cb1 = get_circuit_breaker("test1")
        cb2 = get_circuit_breaker("test2")

        cb1.force_open()
        cb2.force_open()

        # Reset all through monitor
        results = self.monitor.reset_all_circuit_breakers()

        # All should be successfully reset
        self.assertTrue(all(results.values()))
        self.assertEqual(cb1.get_state(), CircuitState.CLOSED)
        self.assertEqual(cb2.get_state(), CircuitState.CLOSED)


async def test_async_circuit_breaker():
    """Test async circuit breaker functionality."""
    config = CircuitBreakerConfig(failure_threshold=2, timeout_duration=0.1)
    cb = CircuitBreaker(config, "async_test")

    async def mock_async_func(should_fail=False):
        await asyncio.sleep(0.01)  # Simulate async work
        if should_fail:
            raise Exception("Async failure")
        return "async_success"

    # Test successful async calls
    result = await cb.call_async(mock_async_func, should_fail=False)
    assert result == "async_success"

    # Test failures
    for _ in range(2):
        try:
            await cb.call_async(mock_async_func, should_fail=True)
        except Exception:
            pass

    # Circuit should be open
    assert cb.get_state() == CircuitState.OPEN

    # Should raise CircuitBreakerOpenError
    try:
        await cb.call_async(mock_async_func, should_fail=False)
        assert False, "Should have raised CircuitBreakerOpenError"
    except CircuitBreakerOpenError:
        pass


def run_async_tests():
    """Run async tests."""
    print("Running async circuit breaker tests...")
    asyncio.run(test_async_circuit_breaker())
    print("Async tests passed!")


if __name__ == "__main__":
    print("Running Circuit Breaker Tests...")

    # Run synchronous tests
    unittest.main(argv=[''], exit=False, verbosity=2)

    # Run async tests
    run_async_tests()

    print("\nAll tests completed!")