# OpenTelemetry WIT Implementation Guide

This guide provides comprehensive documentation for implementing the OpenTelemetry WIT interface for Fermyon Spin components. The interface is designed to be vendor-neutral while supporting both local development (like your local-otel stack) and commercial providers (like Datadog).

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [Core Concepts](#core-concepts)
4. [Implementation Requirements](#implementation-requirements)
5. [Configuration](#configuration)
6. [Feature Details](#feature-details)
7. [Protocol Support](#protocol-support)
8. [Usage Examples](#usage-examples)
9. [Testing](#testing)
10. [Performance Considerations](#performance-considerations)

## Overview

This WIT interface provides a complete OpenTelemetry SDK implementation for WebAssembly Component Model applications, specifically designed for Fermyon Spin. It supports:

- **Traces**: Full distributed tracing with W3C Trace Context
- **Metrics**: All OpenTelemetry metric types with aggregation
- **Logs**: Structured logging with automatic trace correlation
- **Multiple Protocols**: OTLP, StatsD, Jaeger, Prometheus, and more
- **Advanced Features**: Circuit breakers, error tracking, SLI/SLO patterns

## Design Principles

### 1. Vendor Neutrality
The interface avoids vendor-specific features while maintaining compatibility with major providers:
- Uses OpenTelemetry semantic conventions
- Supports standard export protocols
- Allows custom headers for authentication

### 2. WASM Optimization
Designed for WebAssembly constraints:
- Efficient batching to minimize exports
- Client-side aggregation for high-frequency metrics
- Memory-conscious buffering strategies

### 3. Developer Experience
Focuses on ease of use:
- Development mode with verbose output
- Built-in testing utilities
- Automatic context propagation
- Comprehensive error tracking

### 4. Standards Compliance
Follows industry standards:
- OpenTelemetry specification
- W3C Trace Context
- Prometheus exposition format
- StatsD protocol

## Core Concepts

### Resources
Every telemetry signal includes resource attributes identifying the source:
```rust
let config = ProviderConfig {
    service_name: "my-spin-app",
    service_version: Some("1.0.0"),
    environment: Some("production"),
    resource_attributes: vec![
        Attribute {
            key: "host.name".to_string(),
            value: AttributeValue::StringValue("spin-host-1".to_string()),
        }
    ],
    // ...
};
```

### Context Propagation
Automatic propagation of trace context, correlation IDs, and other identifiers:
- Trace ID/Span ID injection in logs
- Request ID tracking
- Session ID correlation
- Correlation IDs for non-traced operations

### Sampling
Configurable sampling strategies to control data volume:
- Always on/off
- Probability-based
- Parent-based (follows upstream decision)

### Error Tracking
Enhanced error tracking with:
- Automatic stack trace capture
- Error fingerprinting for deduplication
- Circuit breaker integration
- Panic handlers

## Implementation Requirements

### Resource Management
Implementations must:
1. Properly manage resource lifecycle (create → use → shutdown)
2. Implement batching for efficient network usage
3. Handle backpressure when queues fill
4. Clean up resources on shutdown

### Thread Safety
While WASM is single-threaded, implementations should:
1. Handle async operations correctly
2. Maintain order of operations
3. Prevent race conditions in callbacks

### Error Handling
All operations return `Result` types. Implementations should:
1. Never panic on errors
2. Provide meaningful error messages
3. Continue operating despite individual failures
4. Log errors to development console in dev mode

## Configuration

### Basic Configuration
```rust
let config = ProviderConfig {
    // Required fields
    endpoint: "http://localhost:4318".to_string(),
    protocol: ExportProtocol::OtlpHttp,
    service_name: "my-service".to_string(),
    
    // Optional fields with defaults
    service_version: None,
    environment: Some("development".to_string()),
    resource_attributes: vec![],
    default_tags: vec![],
    headers: vec![],
    compression: true,
    timeout_ms: 10000,
    batch_size: 512,
    max_queue_size: 2048,
    sampling: SamplingStrategy::AlwaysOn,
    dev_mode: false,
};
```

### Environment-Specific Configuration

#### Local Development (local-otel)
```rust
let config = ProviderConfig {
    endpoint: "http://localhost:4318".to_string(),
    protocol: ExportProtocol::OtlpHttp,
    service_name: "my-spin-app".to_string(),
    environment: Some("local-development".to_string()),
    dev_mode: true,  // Enable verbose output
    // ...
};
```

#### Production (Datadog)
```rust
let config = ProviderConfig {
    endpoint: "https://trace.agent.datadoghq.com".to_string(),
    protocol: ExportProtocol::OtlpHttp,
    service_name: "my-spin-app".to_string(),
    environment: Some("production".to_string()),
    headers: vec![
        ("DD-API-KEY".to_string(), "your-api-key".to_string()),
    ],
    sampling: SamplingStrategy::Probability(0.1), // Sample 10%
    // ...
};
```

## Feature Details

### Metrics

#### Temporality Control
Support both delta and cumulative temporality:
- **Delta**: Reports changes since last export (StatsD-style)
- **Cumulative**: Reports total since start (Prometheus-style)

#### Pre-aggregation
For high-frequency metrics, use client-side aggregation:
```rust
let aggregated = AggregatedMetric {
    metric: metric_point,
    count: 1000,
    window_ms: 60000, // 1 minute window
};
meter.record_aggregated(vec![aggregated])?;
```

#### Exemplars
Link metrics to trace examples:
```rust
let exemplar = Exemplar {
    value: 42.5,
    timestamp_nanos: now(),
    trace_context: Some(current_trace_context),
    attributes: vec![],
};
```

#### Histogram Percentiles
Pre-calculate percentiles for efficient querying:
```rust
let histogram = HistogramData {
    count: 1000,
    sum: 45000.0,
    percentiles: vec![
        Percentile { percentile: 50.0, value: 45.0 },
        Percentile { percentile: 95.0, value: 120.0 },
        Percentile { percentile: 99.0, value: 250.0 },
    ],
    // ...
};
```

### Traces

#### Span Creation
```rust
let span = tracer.start_span(SpanSpec {
    name: "process_request".to_string(),
    kind: SpanKind::Server,
    parent: extracted_context,
    attributes: vec![
        Attribute {
            key: "http.method".to_string(),
            value: AttributeValue::StringValue("POST".to_string()),
        },
    ],
    links: vec![],
    start_time_nanos: None, // Use current time
})?;
```

#### Error Recording
Enhanced error tracking with fingerprinting:
```rust
span.record_error(ErrorInfo {
    message: "Database connection timeout".to_string(),
    error_type: Some("TimeoutError".to_string()),
    stack_trace: Some(capture_stack_trace()),
    fingerprint: Some("TimeoutError:db:connection".to_string()),
    circuit_breaker_triggered: false,
})?;
```

### Logs

#### Automatic Correlation
Logs automatically include trace context:
```rust
let logger = logger.with_trace_context(span.context())?;
logger.emit(LogRecord {
    body: "Processing user request".to_string(),
    severity: SeverityLevel::Info,
    attributes: vec![],
    // These are automatically set
    trace_context: Some(trace_context),
    correlation_id: Some(correlation_id),
    // ...
})?;
```

### SLI/SLO Patterns

#### RED Metrics (Rate, Errors, Duration)
```rust
meter.record_red_metrics(
    "/api/users".to_string(),
    RedMetrics {
        rate: 100.5,              // requests/sec
        error_rate: 0.02,         // 2% errors
        duration_p50: 45.0,       // 45ms median
        duration_p95: 120.0,      // 120ms p95
        duration_p99: 250.0,      // 250ms p99
    }
)?;
```

#### Golden Signals
```rust
meter.record_golden_signals(
    "user-service".to_string(),
    GoldenSignals {
        traffic: 1000.0,          // requests/sec
        error_rate: 0.01,         // 1% errors
        latency_p50: 50.0,        // 50ms median
        latency_p95: 150.0,       // 150ms p95
        latency_p99: 300.0,       // 300ms p99
        saturation: 0.75,         // 75% resource usage
    }
)?;
```

### Circuit Breakers

Prevent cascading failures:
```rust
let breaker = meter.create_circuit_breaker(
    "external-api".to_string(),
    CircuitBreakerConfig {
        error_threshold_percent: 50.0,  // Open at 50% errors
        window_ms: 60000,               // 1 minute window
        min_requests: 10,               // Need 10 requests minimum
        cooldown_ms: 30000,             // 30 second cooldown
    }
)?;

// Use in requests
if !breaker.is_open() {
    match make_request() {
        Ok(_) => breaker.record_success()?,
        Err(_) => breaker.record_error()?,
    }
}
```

## Protocol Support

### OTLP (OpenTelemetry Protocol)
- **HTTP**: Best for compatibility, firewall-friendly
- **gRPC**: More efficient, bidirectional streaming

### StatsD
- UDP-based, fire-and-forget
- Great for high-frequency metrics
- Minimal overhead

### Prometheus
- Pull-based model
- Ideal for Kubernetes environments
- Supports PromQL queries

### Development Mode
- Logs telemetry to stdout
- Human-readable format
- Includes all context information

## Usage Examples

### Complete Spin Component Example

```rust
use spin_sdk::{http_component, http::Request};
use opentelemetry_wit::{Provider, Tracer, Meter, Logger};

#[http_component]
async fn handle_request(req: Request) -> Result<Response, Error> {
    // Initialize provider (once per component)
    let provider = Provider::new(ProviderConfig {
        endpoint: std::env::var("OTEL_ENDPOINT")
            .unwrap_or("http://localhost:4318".to_string()),
        protocol: ExportProtocol::OtlpHttp,
        service_name: "my-spin-app".to_string(),
        environment: Some("production".to_string()),
        default_tags: vec![
            Attribute {
                key: "component".to_string(),
                value: AttributeValue::StringValue("http-handler".to_string()),
            },
        ],
        dev_mode: cfg!(debug_assertions),
        ..Default::default()
    })?;

    let tracer = provider.create_tracer("http-handler", Some("1.0.0"))?;
    let meter = provider.create_meter("http-handler", Some("1.0.0"))?;
    let logger = provider.create_logger("http-handler", Some("1.0.0"))?;

    // Extract trace context from headers
    let trace_context = tracer.extract_context(
        req.headers().iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect()
    );

    // Start span
    let span = tracer.start_span(SpanSpec {
        name: format!("{} {}", req.method(), req.path()),
        kind: SpanKind::Server,
        parent: trace_context,
        attributes: vec![
            Attribute {
                key: "http.method".to_string(),
                value: AttributeValue::StringValue(req.method().to_string()),
            },
            Attribute {
                key: "http.path".to_string(),
                value: AttributeValue::StringValue(req.path().to_string()),
            },
        ],
        ..Default::default()
    })?;

    // Log with trace context
    let trace_logger = logger.with_trace_context(span.context())?;
    trace_logger.emit(LogRecord {
        body: format!("Handling {} request to {}", req.method(), req.path()),
        severity: SeverityLevel::Info,
        ..Default::default()
    })?;

    // Process request (with metrics)
    let start = std::time::Instant::now();
    let result = process_request(req).await;
    let duration = start.elapsed();

    // Record metrics
    meter.record_metrics(vec![
        MetricPoint {
            name: "http.server.duration".to_string(),
            kind: MetricKind::Histogram,
            value: MetricValue::F64Value(duration.as_millis() as f64),
            attributes: vec![
                Attribute {
                    key: "http.method".to_string(),
                    value: AttributeValue::StringValue(req.method().to_string()),
                },
                Attribute {
                    key: "http.status_code".to_string(),
                    value: AttributeValue::S64Value(
                        result.as_ref()
                            .map(|r| r.status() as i64)
                            .unwrap_or(500)
                    ),
                },
            ],
            temporality: MetricTemporality::Delta,
            exemplar: Some(Exemplar {
                value: duration.as_millis() as f64,
                timestamp_nanos: now_nanos(),
                trace_context: Some(span.context()),
                attributes: vec![],
            }),
            ..Default::default()
        },
    ])?;

    // Handle errors
    match result {
        Ok(response) => {
            span.set_status(StatusCode::Ok, None)?;
            Ok(response)
        }
        Err(error) => {
            span.record_error(ErrorInfo {
                message: error.to_string(),
                error_type: Some(std::any::type_name_of_val(&error).to_string()),
                stack_trace: None,
                fingerprint: Some(generate_error_fingerprint(&error)),
                circuit_breaker_triggered: false,
            })?;
            span.set_status(StatusCode::Error, Some(error.to_string()))?;
            Err(error)
        }
    }

    // Span automatically ends when dropped
}
```

## Testing

### Unit Testing with Mock Provider
```rust
#[test]
fn test_telemetry() {
    let test_helper = telemetry_test_helper();
    let provider = test_helper.create_mock_provider()?;
    
    // Use provider normally
    let tracer = provider.create_tracer("test", None)?;
    let span = tracer.start_span(SpanSpec {
        name: "test-span".to_string(),
        ..Default::default()
    })?;
    span.end(None)?;
    
    // Verify telemetry was recorded
    assert!(test_helper.verify_telemetry(
        Some("test-span"),
        None,
        None
    ));
    
    let recorded_spans = test_helper.get_recorded_spans();
    assert_eq!(recorded_spans.len(), 1);
    assert_eq!(recorded_spans[0].name, "test-span");
}
```

### Integration Testing
```rust
// Point to your local-otel stack
let config = ProviderConfig {
    endpoint: "http://localhost:4318".to_string(),
    protocol: ExportProtocol::OtlpHttp,
    service_name: "integration-test".to_string(),
    dev_mode: true,
    ..Default::default()
};

// Verify data appears in files
std::thread::sleep(Duration::from_secs(2));
let traces = std::fs::read_to_string("/data/traces/traces.jsonl")?;
assert!(traces.contains("integration-test"));
```

## Performance Considerations

### Batching
- Default batch size: 512 items
- Batches sent every 1 second or when full
- Adjust based on your traffic patterns

### Sampling
- Use probability sampling in production
- Sample 100% in development
- Consider head-based sampling for predictable overhead

### Aggregation
- Pre-aggregate high-frequency metrics
- Use 1-minute windows for most metrics
- Larger windows for low-priority metrics

### Memory Usage
- Default queue size: 2048 items
- Drops oldest items when full
- Monitor `resource_metrics` for memory pressure

### Network Efficiency
- Enable compression for OTLP
- Use gRPC for streaming scenarios
- Batch similar metrics together

## Best Practices

1. **Initialize Once**: Create providers at component startup, not per-request
2. **Use Context**: Always propagate trace context through your application
3. **Meaningful Names**: Use descriptive span and metric names
4. **Standard Attributes**: Follow OpenTelemetry semantic conventions
5. **Error Handling**: Always handle telemetry errors gracefully
6. **Resource Attributes**: Include enough context to debug issues
7. **Sampling Strategy**: Balance observability needs with costs
8. **Test Coverage**: Include telemetry in your test suite

## Troubleshooting

### No Data Appearing
1. Check endpoint configuration
2. Verify protocol matches backend
3. Enable dev_mode for console output
4. Check for errors in return values

### High Memory Usage
1. Reduce batch size
2. Increase export frequency
3. Enable sampling
4. Check for span leaks (not calling end())

### Performance Impact
1. Use aggregated metrics for high-frequency operations
2. Enable sampling
3. Reduce attribute cardinality
4. Use async exports

## Future Considerations

This WIT interface is designed to evolve with:
- New OpenTelemetry specifications
- Additional protocol support
- Enhanced WASM capabilities
- Performance optimizations

The interface maintains backward compatibility while allowing for future extensions.
