# Circuit Breaker Implementation

This document describes the comprehensive circuit breaker pattern implementation for protecting against cascading API failures in the regender-xyz project.

## Overview

The circuit breaker pattern prevents cascading failures by monitoring API call failures and temporarily stopping requests when failure thresholds are exceeded. This implementation provides:

- **Three-state management**: CLOSED (normal), OPEN (failing), HALF_OPEN (testing recovery)
- **Automatic recovery**: Self-healing after configurable timeout periods
- **Thread-safe operations**: Safe for concurrent use
- **Async support**: Full async/await compatibility
- **Intelligent error categorization**: Different handling for different error types
- **Comprehensive monitoring**: Detailed metrics and health monitoring
- **Fallback mechanisms**: Graceful degradation when services are unavailable

## Architecture

### Core Components

#### 1. Circuit Breaker (`src/utils/circuit_breaker.py`)

**Main Classes:**
- `CircuitState`: Enum defining the three circuit states
- `CircuitBreakerConfig`: Configuration class for thresholds and timeouts
- `CircuitBreakerMetrics`: Metrics and state tracking
- `CircuitBreaker`: Main implementation class
- `CircuitBreakerOpenError`: Exception raised when circuit is open

**Key Features:**
- Configurable failure and success thresholds
- Time-based recovery mechanisms
- Thread-safe with RLock for synchronization
- Support for both sync and async operations
- Comprehensive metrics collection
- Global registry for named circuit breakers

#### 2. Monitoring (`src/utils/circuit_breaker_monitor.py`)

**Main Classes:**
- `CircuitBreakerMonitor`: Centralized monitoring and management
- Health summary generation
- Performance metrics collection
- Circuit breaker management operations

#### 3. LLM Client Integration (`src/providers/llm_client.py`)

**Enhanced Features:**
- Automatic circuit breaker integration for all LLM providers
- Intelligent error categorization:
  - `RateLimitError`: Ignored (doesn't count as failures)
  - `NetworkTimeoutError`: Counts as failure
  - `ServiceUnavailableError`: Counts as failure
  - `APIError`: General failures
- Fallback response mechanism
- Provider-specific circuit breaker instances

## Configuration

### Default Configuration

```python
CircuitBreakerConfig(
    failure_threshold=5,        # Open after 5 consecutive failures
    success_threshold=3,        # Close after 3 successes in half-open
    timeout_duration=60.0,      # Wait 1 minute before trying half-open
    reset_timeout=300.0,        # Reset failure count after 5 minutes
    monitoring_window=60.0,     # Track failures over 1 minute window
    half_open_max_calls=3,      # Allow 3 calls in half-open state
    expected_exceptions=(APIError, ServiceUnavailableError, NetworkTimeoutError),
    ignore_exceptions=(RateLimitError,)  # Rate limits don't count as failures
)
```

### Customization

Circuit breakers can be customized per provider or use case:

```python
from src.utils.circuit_breaker import CircuitBreakerConfig, get_circuit_breaker

# Custom configuration for critical services
critical_config = CircuitBreakerConfig(
    failure_threshold=3,     # More sensitive
    timeout_duration=30.0,   # Faster recovery attempts
)

cb = get_circuit_breaker("critical_service", critical_config)
```

## Usage

### Automatic Integration

Circuit breakers are automatically enabled in the LLM client:

```python
from src.providers.llm_client import get_llm_client

# Circuit breaker enabled by default
client = get_llm_client(provider="openai")

# Disable circuit breaker if needed
client = get_llm_client(provider="openai", enable_circuit_breaker=False)
```

### Manual Usage

```python
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

config = CircuitBreakerConfig(failure_threshold=3)
cb = CircuitBreaker(config, "my_service")

# Synchronous usage
try:
    result = cb.call(my_function, arg1, arg2)
except CircuitBreakerOpenError:
    # Handle circuit open case
    handle_service_unavailable()

# Asynchronous usage
try:
    result = await cb.call_async(my_async_function, arg1, arg2)
except CircuitBreakerOpenError:
    # Handle circuit open case
    await handle_service_unavailable()
```

### Decorator Usage

```python
from src.utils.circuit_breaker import circuit_breaker, CircuitBreakerConfig

config = CircuitBreakerConfig(failure_threshold=5)

@circuit_breaker(config, "api_service")
def call_external_api():
    # Your API call here
    pass

@circuit_breaker(config, "async_service")
async def call_async_api():
    # Your async API call here
    pass
```

## Monitoring and Management

### Health Monitoring

```python
from src.utils.circuit_breaker_monitor import get_circuit_breaker_monitor

monitor = get_circuit_breaker_monitor()

# Get health summary
health = monitor.get_health_summary()
print(f"Overall health: {health['overall_health']}")

# Log comprehensive health report
monitor.log_health_report()

# Get performance metrics
metrics = monitor.get_performance_metrics()
```

### Circuit Breaker Management

```python
# Reset all circuit breakers
results = monitor.reset_all_circuit_breakers()

# Force specific circuit breaker states
monitor.force_open_circuit_breaker("openai_client")
monitor.force_close_circuit_breaker("openai_client")
```

### LLM Client Monitoring

```python
from src.providers.llm_client import get_llm_client

client = get_llm_client()

# Get circuit breaker metrics
metrics = client.get_circuit_breaker_metrics()
if metrics:
    print(f"State: {metrics['state']}")
    print(f"Failure rate: {metrics['failure_rate']:.2%}")

# Manage circuit breaker
client.reset_circuit_breaker()
client.force_circuit_open()  # For testing
client.force_circuit_closed()
```

## Error Handling

### Error Categories

1. **Rate Limit Errors** (`RateLimitError`)
   - **Behavior**: Ignored by circuit breaker
   - **Rationale**: Rate limits are expected and temporary
   - **Handling**: Passed through to application

2. **Network Timeout Errors** (`NetworkTimeoutError`)
   - **Behavior**: Count as failures
   - **Rationale**: Indicate service or network issues
   - **Handling**: Circuit breaker tracks and may open

3. **Service Unavailable Errors** (`ServiceUnavailableError`)
   - **Behavior**: Count as failures
   - **Rationale**: Indicate service is down
   - **Handling**: Circuit breaker tracks and may open

4. **General API Errors** (`APIError`)
   - **Behavior**: Count as failures
   - **Rationale**: Indicate service issues
   - **Handling**: Circuit breaker tracks and may open

### Fallback Mechanism

When the circuit breaker is open, the LLM client can provide fallback responses:

```python
# Fallback enabled (default)
response = client.complete(messages, use_fallback=True)
# Returns: "I apologize, but the AI service is currently experiencing issues..."

# Fallback disabled (raises exception)
try:
    response = client.complete(messages, use_fallback=False)
except APIError as e:
    # Handle service unavailable
    pass
```

## State Transitions

### Normal Flow

1. **CLOSED** → Normal operation
   - All requests pass through
   - Failures are counted
   - Success resets failure count

2. **CLOSED** → **OPEN** (when failure threshold exceeded)
   - Circuit opens immediately
   - All requests are rejected
   - Timer starts for recovery attempt

3. **OPEN** → **HALF_OPEN** (after timeout)
   - Limited requests allowed
   - Testing service recovery
   - Success/failure determines next state

4. **HALF_OPEN** → **CLOSED** (on success threshold)
   - Service has recovered
   - Normal operation resumes
   - Metrics are reset

5. **HALF_OPEN** → **OPEN** (on any failure)
   - Service still failing
   - Circuit opens again
   - Timer resets

## Metrics and Observability

### Available Metrics

- **State Information**: Current state, state uptime, transition counts
- **Call Statistics**: Total calls, successes, failures, failure rate
- **Timing**: Last failure/success times, state change times
- **Configuration**: Active thresholds and timeouts

### Health Status

- **Healthy**: Circuit closed, low failure rate
- **Degraded**: Circuit half-open or elevated failure rate
- **Failed**: Circuit open
- **Error**: Metrics collection failed

## Testing

The implementation includes comprehensive tests:

```bash
# Run circuit breaker tests
python -m pytest tests/test_circuit_breaker.py -v

# Test with LLM integration
python tests/test_circuit_breaker.py
```

## Best Practices

### Configuration Guidelines

1. **Failure Threshold**: 3-5 for critical services, 5-10 for non-critical
2. **Success Threshold**: 2-3 for quick recovery validation
3. **Timeout Duration**: 30-60 seconds for quick recovery, 2-5 minutes for stable services
4. **Monitoring Window**: 60 seconds for responsive failure detection

### Error Handling

1. **Always handle `CircuitBreakerOpenError`** in application code
2. **Implement meaningful fallbacks** for user-facing operations
3. **Log circuit breaker state changes** for debugging
4. **Monitor circuit breaker health** in production

### Performance Considerations

1. **Minimal overhead**: Circuit breaker adds <1ms per call
2. **Thread-safe operations**: Uses efficient RLock synchronization
3. **Memory efficient**: Lightweight metrics collection
4. **Configurable monitoring**: Disable detailed logging in production if needed

## Integration Examples

### Basic LLM Usage

```python
from src.providers.llm_client import get_llm_client

client = get_llm_client(provider="openai")

messages = [{"role": "user", "content": "Hello!"}]

try:
    response = client.complete(messages)
    print(response.content)
except APIError as e:
    print(f"Service error: {e}")
    # Handle gracefully
```

### Custom Service Protection

```python
from src.utils.circuit_breaker import get_circuit_breaker, CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=3,
    timeout_duration=30.0,
)

cb = get_circuit_breaker("external_api", config)

def call_external_service():
    try:
        return cb.call(external_api_call)
    except CircuitBreakerOpenError:
        return get_cached_response()
```

## Conclusion

This circuit breaker implementation provides robust protection against cascading failures while maintaining high performance and ease of use. It automatically integrates with the LLM client infrastructure and provides comprehensive monitoring capabilities for production environments.

The design follows industry best practices and is suitable for high-traffic applications requiring reliable service protection.