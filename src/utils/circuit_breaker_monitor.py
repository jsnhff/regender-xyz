"""
Circuit Breaker Monitoring and Management Utilities

Provides monitoring tools and management functions for circuit breakers
used throughout the application.
"""

import logging
import time
from dataclasses import asdict
from typing import Any, Optional

from .circuit_breaker import CircuitState, get_all_circuit_breakers

logger = logging.getLogger(__name__)


class CircuitBreakerMonitor:
    """Monitor and manage circuit breakers across the application."""

    def __init__(self):
        """Initialize circuit breaker monitor."""
        self.monitoring_enabled = True

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get metrics for all registered circuit breakers."""
        circuit_breakers = get_all_circuit_breakers()
        metrics = {}

        for name, cb in circuit_breakers.items():
            try:
                metrics[name] = cb.get_metrics()
            except Exception as e:
                logger.error(f"Error getting metrics for circuit breaker '{name}': {e}")
                metrics[name] = {"error": str(e)}

        return metrics

    def get_health_summary(self) -> dict[str, Any]:
        """Get a health summary of all circuit breakers."""
        all_metrics = self.get_all_metrics()

        summary = {
            "total_circuit_breakers": len(all_metrics),
            "healthy": 0,
            "degraded": 0,
            "failed": 0,
            "circuit_breakers": {},
            "overall_health": "unknown",
        }

        for name, metrics in all_metrics.items():
            if "error" in metrics:
                status = "error"
                summary["failed"] += 1
            else:
                state = metrics.get("state", "unknown")
                failure_rate = metrics.get("failure_rate", 0.0)

                if state == CircuitState.OPEN.value:
                    status = "failed"
                    summary["failed"] += 1
                elif state == CircuitState.HALF_OPEN.value or failure_rate > 0.2:
                    status = "degraded"
                    summary["degraded"] += 1
                else:
                    status = "healthy"
                    summary["healthy"] += 1

            summary["circuit_breakers"][name] = {
                "status": status,
                "state": metrics.get("state", "unknown"),
                "failure_rate": metrics.get("failure_rate", 0.0),
                "total_calls": metrics.get("total_calls", 0),
                "circuit_open_count": metrics.get("circuit_open_count", 0),
            }

        # Determine overall health
        if summary["failed"] > 0:
            summary["overall_health"] = "critical"
        elif summary["degraded"] > 0:
            summary["overall_health"] = "degraded"
        elif summary["healthy"] > 0:
            summary["overall_health"] = "healthy"
        else:
            summary["overall_health"] = "unknown"

        return summary

    def log_health_report(self, level: str = "info") -> None:
        """Log a comprehensive health report."""
        summary = self.get_health_summary()

        log_func = getattr(logger, level.lower(), logger.info)

        log_func("Circuit Breaker Health Report:")
        log_func(f"  Overall Health: {summary['overall_health'].upper()}")
        log_func(f"  Total Circuit Breakers: {summary['total_circuit_breakers']}")
        log_func(f"  Healthy: {summary['healthy']}")
        log_func(f"  Degraded: {summary['degraded']}")
        log_func(f"  Failed: {summary['failed']}")

        for name, status in summary["circuit_breakers"].items():
            status_indicator = (
                "✓"
                if status["status"] == "healthy"
                else "⚠"
                if status["status"] == "degraded"
                else "✗"
            )
            log_func(
                f"  {status_indicator} {name}: {status['state']} "
                f"(failure_rate: {status['failure_rate']:.2%})"
            )

    def reset_all_circuit_breakers(self) -> dict[str, bool]:
        """Reset all circuit breakers to closed state."""
        circuit_breakers = get_all_circuit_breakers()
        results = {}

        for name, cb in circuit_breakers.items():
            try:
                cb.reset()
                results[name] = True
                logger.info(f"Reset circuit breaker: {name}")
            except Exception as e:
                results[name] = False
                logger.error(f"Failed to reset circuit breaker '{name}': {e}")

        return results

    def get_circuit_breaker_by_name(self, name: str) -> Optional[Any]:
        """Get a specific circuit breaker by name."""
        circuit_breakers = get_all_circuit_breakers()
        return circuit_breakers.get(name)

    def force_open_circuit_breaker(self, name: str) -> bool:
        """Force a specific circuit breaker to open state."""
        cb = self.get_circuit_breaker_by_name(name)
        if cb:
            try:
                cb.force_open()
                logger.warning(f"Forced circuit breaker '{name}' to open state")
                return True
            except Exception as e:
                logger.error(f"Failed to force open circuit breaker '{name}': {e}")
                return False
        else:
            logger.error(f"Circuit breaker '{name}' not found")
            return False

    def force_close_circuit_breaker(self, name: str) -> bool:
        """Force a specific circuit breaker to closed state."""
        cb = self.get_circuit_breaker_by_name(name)
        if cb:
            try:
                cb.force_close()
                logger.info(f"Forced circuit breaker '{name}' to closed state")
                return True
            except Exception as e:
                logger.error(f"Failed to force close circuit breaker '{name}': {e}")
                return False
        else:
            logger.error(f"Circuit breaker '{name}' not found")
            return False

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance-focused metrics for all circuit breakers."""
        all_metrics = self.get_all_metrics()

        performance_summary = {
            "total_calls": 0,
            "total_failures": 0,
            "total_successes": 0,
            "overall_failure_rate": 0.0,
            "average_response_time": 0.0,  # Not implemented yet, placeholder
            "circuit_breakers": {},
        }

        for name, metrics in all_metrics.items():
            if "error" not in metrics:
                total_calls = metrics.get("total_calls", 0)
                total_failures = metrics.get("total_failures", 0)
                total_successes = metrics.get("total_successes", 0)

                performance_summary["total_calls"] += total_calls
                performance_summary["total_failures"] += total_failures
                performance_summary["total_successes"] += total_successes

                performance_summary["circuit_breakers"][name] = {
                    "calls_per_minute": total_calls,  # Simplified, would need time window
                    "failure_rate": metrics.get("failure_rate", 0.0),
                    "state": metrics.get("state", "unknown"),
                    "circuit_opens": metrics.get("circuit_open_count", 0),
                }

        if performance_summary["total_calls"] > 0:
            performance_summary["overall_failure_rate"] = (
                performance_summary["total_failures"] / performance_summary["total_calls"]
            )

        return performance_summary


# Global monitor instance
_monitor_instance: Optional[CircuitBreakerMonitor] = None


def get_circuit_breaker_monitor() -> CircuitBreakerMonitor:
    """Get the global circuit breaker monitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = CircuitBreakerMonitor()
    return _monitor_instance


def log_circuit_breaker_health(level: str = "info") -> None:
    """Convenience function to log circuit breaker health."""
    monitor = get_circuit_breaker_monitor()
    monitor.log_health_report(level)


def reset_all_circuit_breakers() -> dict[str, bool]:
    """Convenience function to reset all circuit breakers."""
    monitor = get_circuit_breaker_monitor()
    return monitor.reset_all_circuit_breakers()


def get_circuit_breaker_health_summary() -> dict[str, Any]:
    """Convenience function to get health summary."""
    monitor = get_circuit_breaker_monitor()
    return monitor.get_health_summary()
