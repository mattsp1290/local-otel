# 📐 Common Telemetry Patterns

This guide presents universal telemetry patterns that apply across all programming languages and frameworks. Use these patterns to ensure consistent, high-quality observability in your applications.

## 🎯 Core Principles

### 1. The Three Pillars of Observability
- **Traces**: Track request flow through your system
- **Metrics**: Measure system performance and business KPIs
- **Logs**: Record detailed events with contextual information

### 2. Correlation is Key
Always correlate your telemetry data:
```
Trace ID ←→ Logs ←→ Metrics
```

## 🔍 Tracing Patterns

### Pattern 1: Span Hierarchy
Structure your spans to reflect logical operations:

```
[HTTP Request] (parent span)
  └── [Authentication] (child span)
  └── [Database Query] (child span)
      └── [Cache Check] (nested child)
      └── [SQL Execution] (nested child)
  └── [Response Serialization] (child span)
```

### Pattern 2: Semantic Conventions
Always use standard attribute names:

```python
# Good - follows OpenTelemetry semantic conventions
span.set_attribute("http.method", "POST")
span.set_attribute("http.route", "/api/users")
span.set_attribute("http.status_code", 200)

# Bad - custom naming
span.set_attribute("method", "POST")
span.set_attribute("endpoint", "/api/users")
span.set_attribute("status", 200)
```

### Pattern 3: Error Handling
Properly record errors in spans:

```python
try:
    # Your code here
    result = process_data()
except Exception as e:
    span.set_status(Status(StatusCode.ERROR, str(e)))
    span.record_exception(e)
    # Also increment error metrics
    metrics.increment("errors", tags=["operation:process_data"])
    raise
```

### Pattern 4: Async Context Propagation
Ensure trace context flows through async operations:

```python
# Python example
async def process_async():
    # Context automatically propagated in async/await
    with tracer.start_as_current_span("async_operation"):
        result = await external_api_call()
        return result

# For manual propagation
context = trace.get_current_span().get_span_context()
# Pass context to background jobs, message queues, etc.
```

## 📊 Metrics Patterns

### Pattern 1: Metric Types and Usage

| Metric Type | Use Case | Example |
|------------|----------|---------|
| Counter | Count occurrences | Request count, errors |
| Gauge | Current value | Queue size, active connections |
| Histogram | Distribution of values | Request duration, payload size |

### Pattern 2: Consistent Naming
Follow these conventions:
- Use lowercase with underscores
- Include unit in name
- Be descriptive but concise

```
✅ Good names:
- http_request_duration_seconds
- database_connections_active
- payment_amount_dollars
- queue_size_messages

❌ Bad names:
- RequestTime
- db_conns
- amt
- qSize
```

### Pattern 3: Essential Metrics
Every service should track:

```python
# 1. RED Method (Request, Error, Duration)
metrics.increment("requests", tags=["endpoint:/api/users", "method:POST"])
metrics.increment("errors", tags=["endpoint:/api/users", "error:timeout"])
metrics.histogram("request_duration_ms", elapsed_time, tags=["endpoint:/api/users"])

# 2. USE Method (Utilization, Saturation, Errors)
metrics.gauge("cpu_utilization_percent", cpu_usage)
metrics.gauge("memory_saturation_percent", memory_pressure)
metrics.increment("system_errors", tags=["type:oom"])

# 3. Business Metrics
metrics.increment("user_signups", tags=["plan:premium"])
metrics.histogram("order_value_dollars", order.total)
metrics.gauge("inventory_count", current_inventory, tags=["sku:ABC123"])
```

### Pattern 4: Tag Strategy
Use consistent tags for filtering and grouping:

```python
# Environment tags
tags = [
    "env:production",
    "region:us-east-1",
    "service:payment-api",
    "version:2.1.0"
]

# Request-specific tags
tags.extend([
    "endpoint:/charge",
    "customer_tier:premium",
    "payment_method:card"
])

metrics.increment("payment_processed", tags=tags)
```

## 📝 Logging Patterns

### Pattern 1: Structured Logging
Always use structured formats (JSON):

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "service": "payment-api",
  "trace_id": "5c9e7c8b3d4f2a1b",
  "span_id": "7a8b9c0d1e2f3a4b",
  "user_id": "user_123",
  "message": "Payment processed successfully",
  "payment": {
    "amount": 99.99,
    "currency": "USD",
    "method": "card"
  }
}
```

### Pattern 2: Log Levels
Use appropriate log levels:

| Level | Use Case | Example |
|-------|----------|---------|
| DEBUG | Detailed debugging info | Variable values, function entry/exit |
| INFO | General information | Request received, payment processed |
| WARNING | Potentially harmful | High memory usage, deprecated API usage |
| ERROR | Error events | Failed database connection, API timeout |
| CRITICAL | Critical problems | System out of memory, data corruption |

### Pattern 3: Contextual Information
Include relevant context in every log:

```python
logger.info("Processing order", extra={
    "order_id": order.id,
    "user_id": user.id,
    "total_amount": order.total,
    "item_count": len(order.items),
    "trace_id": current_trace_id,
    "span_id": current_span_id
})
```

### Pattern 4: Security Considerations
Never log sensitive data:

```python
# ❌ Bad - logs sensitive data
logger.info(f"User login: {username}, password: {password}")

# ✅ Good - logs safely
logger.info("User login attempt", extra={
    "username": username,
    "ip_address": request.remote_addr,
    "user_agent": request.user_agent
})
```

## 🔗 Correlation Patterns

### Pattern 1: Trace-Log Correlation
Inject trace context into all logs:

```python
# Python example
span = trace.get_current_span()
if span and span.is_recording():
    ctx = span.get_span_context()
    log_extra = {
        "trace_id": format(ctx.trace_id, '032x'),
        "span_id": format(ctx.span_id, '016x')
    }
    logger.info("Processing request", extra=log_extra)
```

### Pattern 2: Request ID Propagation
Generate and propagate request IDs:

```python
# Generate at edge
request_id = str(uuid.uuid4())

# Add to headers
headers["X-Request-ID"] = request_id

# Include in all telemetry
span.set_attribute("request.id", request_id)
logger.info("Request received", extra={"request_id": request_id})
metrics.increment("requests", tags=[f"request_id:{request_id}"])
```

### Pattern 3: Baggage for Business Context
Use OpenTelemetry Baggage for cross-service context:

```python
from opentelemetry import baggage

# Set baggage at entry point
baggage.set_baggage("user.tier", "premium")
baggage.set_baggage("feature.flag", "new-checkout-flow")

# Access anywhere in the request flow
user_tier = baggage.get_baggage("user.tier")
```

## 🏭 Production Patterns

### Pattern 1: Sampling Strategy
Implement intelligent sampling:

```python
# Head-based sampling
if should_sample(request):
    with tracer.start_as_current_span("operation") as span:
        span.set_attribute("sampling.decision", "sampled")

# Tail-based sampling signals
span.set_attribute("sampling.priority", 2)  # Force sampling
span.set_attribute("error", True)  # Sample all errors
```

### Pattern 2: High Cardinality Protection
Limit unique tag values:

```python
# ❌ Bad - unbounded cardinality
metrics.increment("requests", tags=[f"user_id:{user_id}"])

# ✅ Good - bounded cardinality
user_tier = get_user_tier(user_id)  # Returns: free, pro, enterprise
metrics.increment("requests", tags=[f"user_tier:{user_tier}"])
```

### Pattern 3: Circuit Breaker for Telemetry
Protect against telemetry system failures:

```python
class TelemetryCircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=60):
        self.failure_count = 0
        self.is_open = False
        
    def record_span(self, span_data):
        if self.is_open:
            return  # Skip telemetry
            
        try:
            export_span(span_data)
            self.failure_count = 0
        except Exception:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                self.schedule_reset()
```

## 🎯 Anti-Patterns to Avoid

### 1. Over-instrumentation
```python
# ❌ Bad - too granular
with tracer.start_as_current_span("get_user_name"):
    name = user.name  # This is too simple to trace

# ✅ Good - meaningful operations
with tracer.start_as_current_span("fetch_user_profile"):
    profile = database.get_user_profile(user_id)
```

### 2. Missing Error Context
```python
# ❌ Bad - no context
logger.error("Operation failed")

# ✅ Good - rich context
logger.error("Failed to process payment", extra={
    "error": str(e),
    "payment_id": payment_id,
    "amount": amount,
    "retry_count": retry_count
})
```

### 3. Synchronous Telemetry Export
```python
# ❌ Bad - blocks application
span.end()
exporter.export_immediately(span)  # Blocks!

# ✅ Good - async/batched export
span.end()  # Non-blocking, handled by SDK
```

## 📚 Further Reading

- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/reference/specification/trace/semantic_conventions/)
- [Distributed Tracing Best Practices](https://www.w3.org/TR/trace-context/)
- [StatsD Metric Types](https://github.com/statsd/statsd/blob/master/docs/metric_types.md)
- [Structured Logging Guidelines](https://www.structlog.org/en/stable/why.html)

---

Remember: Good telemetry is like good documentation - it should tell a story about what your system is doing, why it's doing it, and how well it's performing.
